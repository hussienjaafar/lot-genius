"""
Lightweight calibration scaffold for model feedback and adjustment.

Provides logging of model predictions, ingestion of realized outcomes,
computation of calibration metrics, and generation of adjustment suggestions.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .config import settings


def log_predictions(
    items_df: pd.DataFrame, context: Dict[str, Any], out_jsonl: str
) -> int:
    """
    Log model predictions to JSONL for later calibration analysis.

    Args:
        items_df: DataFrame with model outputs (price, sell_p60, etc.)
        context: Additional context (roi_target, risk_threshold, etc.)
        out_jsonl: Output JSONL file path

    Returns:
        Number of records written
    """
    if items_df.empty:
        return 0

    out_path = Path(out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    horizon_days = context.get("horizon_days", settings.SELLTHROUGH_HORIZON_DAYS)

    records = []
    for idx, row in items_df.iterrows():
        record = {
            # Core identifiers
            "sku_local": row.get("sku_local"),
            "asin": row.get("asin"),
            "upc": row.get("upc"),
            "ean": row.get("ean"),
            "upc_ean_asin": row.get("upc_ean_asin"),
            # Price predictions
            "est_price_mu": _safe_float(row.get("est_price_mu")),
            "est_price_sigma": _safe_float(row.get("est_price_sigma")),
            "est_price_p50": _safe_float(row.get("est_price_p50")),
            # Sell-through predictions
            "sell_p60": _safe_float(row.get("sell_p60")),
            "sell_hazard_daily": _safe_float(row.get("sell_hazard_daily")),
            # Condition and seasonality factors
            "condition_bucket": row.get("condition_bucket"),
            "sell_condition_factor": _safe_float(row.get("sell_condition_factor")),
            "sell_seasonality_factor": _safe_float(row.get("sell_seasonality_factor")),
            # Throughput and operational
            "mins_per_unit": _safe_float(row.get("mins_per_unit")),
            "quantity": _safe_int(row.get("quantity", 1)),
            # Context from optimization
            "horizon_days": horizon_days,
            "roi_target": context.get("roi_target"),
            "risk_threshold": context.get("risk_threshold"),
            "lot_id": context.get("lot_id"),
            "timestamp": timestamp,
        }

        # Add aliases for downstream compatibility
        if record.get("est_price_mu") is not None:
            record["predicted_price"] = record["est_price_mu"]
        if record.get("sell_p60") is not None:
            record["predicted_sell_p60"] = record["sell_p60"]

        # Add nested context object (mirrors logging context plus timestamp)
        record["context"] = {
            "roi_target": context.get("roi_target"),
            "risk_threshold": context.get("risk_threshold"),
            "horizon_days": horizon_days,
            "lot_id": context.get("lot_id"),
            "opt_source": context.get("opt_source"),
            "opt_params": context.get("opt_params"),
            "timestamp": timestamp,
        }
        # Filter out None values from nested context
        record["context"] = {
            k: v for k, v in record["context"].items() if v is not None
        }

        # Filter out None values for cleaner JSONL
        record = {k: v for k, v in record.items() if v is not None}
        records.append(record)

    # Write JSONL in append mode
    with open(out_path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(records)


def load_predictions(jsonl_path: str) -> pd.DataFrame:
    """
    Load predictions from JSONL file.

    Args:
        jsonl_path: Path to JSONL file with predictions

    Returns:
        DataFrame with prediction records
    """
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def load_outcomes(csv_path: str) -> pd.DataFrame:
    """
    Load realized outcomes from CSV.

    Expected columns:
    - sku_local: Identifier matching predictions
    - realized_price: Actual sale price (optional)
    - sold_within_horizon: Boolean/int indicating if sold within horizon
    - days_to_sale: Days from listing to sale (optional)

    Args:
        csv_path: Path to outcomes CSV

    Returns:
        Normalized DataFrame with outcomes
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # Normalize column names (case insensitive, handle variations)
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in ["sku_local", "sku", "item_sku", "local_sku"]:
            col_mapping[col] = "sku_local"
        elif col_lower in [
            "realized_price",
            "actual_price",
            "sale_price",
            "sold_price",
        ]:
            col_mapping[col] = "realized_price"
        elif col_lower in ["sold_within_horizon", "sold", "sold_in_horizon"]:
            col_mapping[col] = "sold_within_horizon"
        elif col_lower in ["days_to_sale", "holding_days", "days_held"]:
            col_mapping[col] = "days_to_sale"

    df = df.rename(columns=col_mapping)

    # Validate required columns
    if "sku_local" not in df.columns:
        raise ValueError("Outcomes CSV must contain a sku_local identifier column")

    # Ensure sold_within_horizon is boolean
    if "sold_within_horizon" in df.columns:
        df["sold_within_horizon"] = df["sold_within_horizon"].astype(bool)

    # Ensure numeric columns are properly typed
    for col in ["realized_price", "days_to_sale"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def join_predictions_outcomes(
    preds: pd.DataFrame, outcomes: pd.DataFrame
) -> pd.DataFrame:
    """
    Join predictions with outcomes on sku_local.

    Args:
        preds: Predictions DataFrame
        outcomes: Outcomes DataFrame

    Returns:
        Inner joined DataFrame
    """
    if len(preds) == 0 or len(outcomes) == 0:
        return pd.DataFrame()

    # Ensure both have sku_local
    if "sku_local" not in preds.columns or "sku_local" not in outcomes.columns:
        raise ValueError("Both predictions and outcomes must have sku_local column")

    # Inner join on sku_local
    joined = preds.merge(
        outcomes, on="sku_local", how="inner", suffixes=("_pred", "_actual")
    )

    return joined


def compute_metrics(df: pd.DataFrame, horizon_days: int) -> Dict[str, Any]:
    """
    Compute calibration and accuracy metrics.

    Args:
        df: Joined predictions/outcomes DataFrame
        horizon_days: Horizon for probability calibration

    Returns:
        Dictionary with computed metrics
    """
    metrics = {
        "n_samples": len(df),
        "horizon_days": horizon_days,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Price prediction metrics
    if "est_price_mu" in df.columns and "realized_price" in df.columns:
        price_mask = df["realized_price"].notna() & df["est_price_mu"].notna()
        if price_mask.sum() > 0:
            pred_prices = df.loc[price_mask, "est_price_mu"]
            actual_prices = df.loc[price_mask, "realized_price"]

            # Mean Absolute Error
            mae = abs(pred_prices - actual_prices).mean()

            # Root Mean Squared Error
            rmse = ((pred_prices - actual_prices) ** 2).mean() ** 0.5

            # Mean Absolute Percentage Error (guard against zero prices)
            mape_mask = actual_prices > 0.01
            if mape_mask.sum() > 0:
                mape = (
                    abs(pred_prices[mape_mask] - actual_prices[mape_mask])
                    / actual_prices[mape_mask]
                ).mean()
            else:
                mape = None

            metrics["price_metrics"] = {
                "mae": float(mae),
                "rmse": float(rmse),
                "mape": float(mape) if mape is not None else None,
                "n_samples": int(price_mask.sum()),
            }

    # Probability calibration metrics
    if "sell_p60" in df.columns and "sold_within_horizon" in df.columns:
        prob_mask = df["sell_p60"].notna() & df["sold_within_horizon"].notna()
        if prob_mask.sum() > 0:
            pred_probs = df.loc[prob_mask, "sell_p60"]
            actual_outcomes = df.loc[prob_mask, "sold_within_horizon"].astype(int)

            # Brier score
            brier_score = ((pred_probs - actual_outcomes) ** 2).mean()

            # Calibration by bins
            bin_edges = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            bin_labels = [
                f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}"
                for i in range(len(bin_edges) - 1)
            ]

            calibration_bins = []
            for i in range(len(bin_edges) - 1):
                bin_mask = (pred_probs >= bin_edges[i]) & (
                    pred_probs < bin_edges[i + 1]
                )
                if i == len(bin_edges) - 2:  # Last bin includes 1.0
                    bin_mask |= pred_probs == 1.0

                if bin_mask.sum() > 0:
                    bin_pred_mean = pred_probs[bin_mask].mean()
                    bin_actual_rate = actual_outcomes[bin_mask].mean()
                    calibration_bins.append(
                        {
                            "bin": bin_labels[i],
                            "n_samples": int(bin_mask.sum()),
                            "pred_mean": float(bin_pred_mean),
                            "actual_rate": float(bin_actual_rate),
                            "bias": float(bin_pred_mean - bin_actual_rate),
                        }
                    )

            metrics["probability_metrics"] = {
                "brier_score": float(brier_score),
                "calibration_bins": calibration_bins,
                "n_samples": int(prob_mask.sum()),
            }

    # Holding days calibration
    if all(
        col in df.columns
        for col in ["sell_hazard_daily", "days_to_sale", "sold_within_horizon"]
    ):
        hazard_mask = (
            df["sell_hazard_daily"].notna()
            & df["days_to_sale"].notna()
            & df["sold_within_horizon"]
            == True
        )

        if hazard_mask.sum() > 0:
            hazards = df.loc[hazard_mask, "sell_hazard_daily"]
            actual_days = df.loc[hazard_mask, "days_to_sale"]

            # Predicted holding days: min(1/lambda, horizon)
            pred_days = (1.0 / hazards.clip(lower=1e-6)).clip(upper=horizon_days)

            holding_mae = abs(pred_days - actual_days).mean()
            holding_median_error = (pred_days - actual_days).median()

            metrics["holding_days_metrics"] = {
                "mae": float(holding_mae),
                "median_error": float(holding_median_error),
                "n_samples": int(hazard_mask.sum()),
            }

    return metrics


def suggest_adjustments(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Suggest model parameter adjustments based on prediction vs outcome analysis.

    Args:
        df: Joined predictions/outcomes DataFrame

    Returns:
        Dictionary with adjustment suggestions
    """
    suggestions = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(df),
    }

    # Condition price factor adjustments
    if all(
        col in df.columns
        for col in ["condition_bucket", "est_price_mu", "realized_price"]
    ):
        condition_mask = (
            df["condition_bucket"].notna()
            & df["est_price_mu"].notna()
            & df["realized_price"].notna()
            & (df["est_price_mu"] > 0.01)  # Avoid division by near-zero
            & (df["realized_price"] > 0.01)
        )

        if condition_mask.sum() > 2:  # Need minimum samples
            condition_adjustments = {}

            for condition in df.loc[condition_mask, "condition_bucket"].unique():
                cond_mask = condition_mask & (df["condition_bucket"] == condition)
                if cond_mask.sum() >= 2:  # Minimum samples per condition
                    ratios = (
                        df.loc[cond_mask, "realized_price"]
                        / df.loc[cond_mask, "est_price_mu"]
                    )
                    median_ratio = ratios.median()

                    # Current factor from settings
                    current_factor = settings.CONDITION_PRICE_FACTOR.get(condition, 1.0)

                    # Suggested new factor (bounded to reasonable range)
                    suggested_factor = current_factor * median_ratio
                    suggested_factor = max(
                        0.3, min(1.5, suggested_factor)
                    )  # Bound [0.3, 1.5]

                    condition_adjustments[condition] = {
                        "current_factor": float(current_factor),
                        "median_ratio": float(median_ratio),
                        "suggested_factor": float(suggested_factor),
                        "n_samples": int(cond_mask.sum()),
                    }

            if condition_adjustments:
                suggestions["condition_price_factors"] = condition_adjustments

    # Category alpha scaling suggestions (placeholder)
    if all(
        col in df.columns
        for col in ["days_to_sale", "sell_hazard_daily", "sold_within_horizon"]
    ):
        # Simple heuristic: if we have category info and holding days data
        holding_mask = (
            df["days_to_sale"].notna()
            & df["sell_hazard_daily"].notna()
            & (df["sold_within_horizon"] == True)
            & (df["sell_hazard_daily"] > 1e-6)
        )

        if holding_mask.sum() >= 5:  # Need reasonable sample size
            actual_days = df.loc[holding_mask, "days_to_sale"]
            hazards = df.loc[holding_mask, "sell_hazard_daily"]
            pred_days = 1.0 / hazards

            # Overall bias in holding days prediction
            median_ratio = (actual_days / pred_days).median()

            suggestions["survival_alpha_scaling"] = {
                "median_holding_days_ratio": float(median_ratio),
                "suggestion": f"Consider adjusting survival alpha by factor of {median_ratio:.3f}",
                "n_samples": int(holding_mask.sum()),
            }

    return suggestions


def write_suggestions(suggestions: Dict[str, Any], path: str) -> None:
    """
    Write adjustment suggestions to JSON file.

    Args:
        suggestions: Suggestions dictionary
        path: Output JSON file path
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)


def _safe_float(value: Any) -> Optional[float]:
    """Convert value to float, return None if not possible."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Convert value to int, return None if not possible."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
