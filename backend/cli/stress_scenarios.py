"""
Stress test scenarios CLI for optimizer.

Runs optimizer across various stress scenarios (price down, returns up, etc.)
and outputs concise CSV/JSON summaries for reports and review.
"""

import json
from pathlib import Path
from typing import Any, Dict

import click
import numpy as np
import pandas as pd
from lotgenius.roi import DEFAULTS, optimize_bid


def _to_json_serializable(obj):
    """Convert numpy arrays to lists for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    else:
        return obj


def apply_scenario_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Baseline scenario: no changes."""
    return df.copy()


def apply_scenario_price_down_15(df: pd.DataFrame) -> pd.DataFrame:
    """Price down 15%: multiply price estimates by 0.85."""
    df_copy = df.copy()

    # Multiply price fields by 0.85, clip at 0
    price_fields = ["est_price_mu", "est_price_sigma"]
    for field in price_fields:
        if field in df_copy.columns:
            df_copy[field] = np.maximum(0, df_copy[field] * 0.85)

    # Handle price percentiles if present
    percentile_fields = [
        col for col in df_copy.columns if col.startswith("est_price_p")
    ]
    for field in percentile_fields:
        df_copy[field] = np.maximum(0, df_copy[field] * 0.85)

    return df_copy


def apply_scenario_returns_up_30(df: pd.DataFrame) -> pd.DataFrame:
    """Returns up 30%: increase return rate by 30%."""
    df_copy = df.copy()

    # Get base return rate from data or use 0.08 default
    base_return_rate = (
        df_copy.get("return_rate", 0.08).iloc[0]
        if "return_rate" in df_copy.columns
        else 0.08
    )
    if pd.isna(base_return_rate):
        base_return_rate = 0.08

    # Increase by 30%, cap at 1.0
    new_return_rate = min(1.0, base_return_rate * 1.30)
    df_copy["return_rate"] = new_return_rate

    return df_copy


def apply_scenario_shipping_up_20(df: pd.DataFrame) -> pd.DataFrame:
    """Shipping up 20%: increase shipping cost by 20%."""
    df_copy = df.copy()

    # Get base shipping from data or use 0.0 default
    base_shipping = (
        df_copy.get("shipping_per_order", 0.0).iloc[0]
        if "shipping_per_order" in df_copy.columns
        else 0.0
    )
    if pd.isna(base_shipping):
        base_shipping = 0.0

    # Increase by 20% (0 stays 0)
    new_shipping = base_shipping * 1.20
    df_copy["shipping_per_order"] = new_shipping

    return df_copy


def apply_scenario_sell_p60_down_10(df: pd.DataFrame) -> pd.DataFrame:
    """Sell-through down 10%: multiply sell_p60 by 0.90."""
    df_copy = df.copy()

    if "sell_p60" in df_copy.columns:
        # Multiply by 0.90 and clip to [0,1]
        df_copy["sell_p60"] = np.clip(df_copy["sell_p60"] * 0.90, 0, 1)

    return df_copy


# Scenario registry
SCENARIOS = {
    "baseline": apply_scenario_baseline,
    "price_down_15": apply_scenario_price_down_15,
    "returns_up_30": apply_scenario_returns_up_30,
    "shipping_up_20": apply_scenario_shipping_up_20,
    "sell_p60_down_10": apply_scenario_sell_p60_down_10,
}

DEFAULT_SCENARIOS = [
    "baseline",
    "price_down_15",
    "returns_up_30",
    "shipping_up_20",
    "sell_p60_down_10",
]


def run_scenario(
    df: pd.DataFrame,
    scenario_name: str,
    lo: float,
    hi: float,
    tol: float,
    sims: int,
    **base_optimizer_kwargs,
) -> Dict[str, Any]:
    """Run optimizer for a single scenario and return summary."""
    # Apply scenario transformation
    scenario_func = SCENARIOS[scenario_name]
    scenario_df = scenario_func(df)

    # Prepare optimizer kwargs, removing any that should come from scenario data
    optimizer_kwargs = base_optimizer_kwargs.copy()

    # Let scenario-transformed data override default kwargs for certain parameters
    if "return_rate" in scenario_df.columns and not bool(
        scenario_df["return_rate"].isna().all()
    ):
        # Use return_rate from transformed data instead of default
        if "return_rate" in optimizer_kwargs:
            del optimizer_kwargs["return_rate"]

    if "shipping_per_order" in scenario_df.columns and not bool(
        scenario_df["shipping_per_order"].isna().all()
    ):
        # Use shipping_per_order from transformed data instead of default
        if "shipping_per_order" in optimizer_kwargs:
            del optimizer_kwargs["shipping_per_order"]

    # Run optimizer
    result = optimize_bid(
        scenario_df, lo=lo, hi=hi, tol=tol, sims=sims, **optimizer_kwargs
    )

    # Extract key metrics
    summary = {
        "scenario": scenario_name,
        "recommended_bid": result.get(
            "bid"
        ),  # optimizer returns 'bid', not 'recommended_bid'
        "roi_p50": result.get("roi_p50"),
        "prob_roi_ge_target": result.get("prob_roi_ge_target"),
        "expected_cash_60d": result.get("expected_cash_60d"),
        "meets_constraints": result.get("meets_constraints"),
    }

    # Add optional metrics if available
    if "roi_p5" in result:
        summary["roi_p5"] = result["roi_p5"]
    if "roi_p95" in result:
        summary["roi_p95"] = result["roi_p95"]
    if "cash_60d_p5" in result:
        summary["cash_60d_p5"] = result["cash_60d_p5"]

    return summary


@click.command()
@click.argument(
    "input_csv", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--out-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output CSV path for stress test results",
)
@click.option(
    "--out-json",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional output JSON path for stress test results",
)
@click.option(
    "--scenarios",
    default="default",
    help="Comma-separated scenario names or 'default' for built-in set",
)
@click.option(
    "--roi-target",
    default=DEFAULTS["roi_target"],
    show_default=True,
    type=float,
    help="ROI target threshold",
)
@click.option(
    "--risk-threshold",
    default=DEFAULTS["risk_threshold"],
    show_default=True,
    type=float,
    help="Risk threshold (probability of meeting ROI target)",
)
@click.option(
    "--lo",
    default=10.0,
    show_default=True,
    type=float,
    help="Lower bound for bid optimization",
)
@click.option(
    "--hi",
    default=10000.0,
    show_default=True,
    type=float,
    help="Upper bound for bid optimization",
)
@click.option(
    "--tol",
    default=10.0,
    show_default=True,
    type=float,
    help="Tolerance for bid optimization",
)
@click.option(
    "--sims",
    default=DEFAULTS["sims"],
    show_default=True,
    type=int,
    help="Number of Monte Carlo simulations",
)
def main(
    input_csv: Path,
    out_csv: Path,
    out_json: Path,
    scenarios: str,
    roi_target: float,
    risk_threshold: float,
    lo: float,
    hi: float,
    tol: float,
    sims: int,
):
    """
    Run optimizer stress tests across multiple scenarios.

    Applies scenario-specific parameter tweaks and runs optimize_bid
    for each scenario, outputting a summary CSV/JSON with key metrics.
    """
    # Read input data
    df = pd.read_csv(input_csv, encoding="utf-8")

    # Parse scenarios
    if scenarios == "default":
        scenario_names = DEFAULT_SCENARIOS
    else:
        scenario_names = [s.strip() for s in scenarios.split(",")]

    # Validate scenarios
    for name in scenario_names:
        if name not in SCENARIOS:
            raise click.ClickException(
                f"Unknown scenario: {name}. Available: {list(SCENARIOS.keys())}"
            )

    # Optimizer kwargs from DEFAULTS and CLI overrides
    optimizer_kwargs = {
        "roi_target": roi_target,
        "risk_threshold": risk_threshold,
        "salvage_frac": DEFAULTS["salvage_frac"],
        "marketplace_fee_pct": DEFAULTS["marketplace_fee_pct"],
        "payment_fee_pct": DEFAULTS["payment_fee_pct"],
        "per_order_fee_fixed": DEFAULTS["per_order_fee_fixed"],
        "shipping_per_order": DEFAULTS["shipping_per_order"],
        "packaging_per_order": DEFAULTS["packaging_per_order"],
        "refurb_per_order": DEFAULTS["refurb_per_order"],
        "return_rate": DEFAULTS["return_rate"],
        "salvage_fee_pct": DEFAULTS["salvage_fee_pct"],
    }

    # Run scenarios
    results = []
    for scenario_name in scenario_names:
        click.echo(f"Running scenario: {scenario_name}")
        summary = run_scenario(df, scenario_name, lo, hi, tol, sims, **optimizer_kwargs)
        results.append(summary)

    # Create output directories
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV output
    results_df = pd.DataFrame(results)
    results_df.to_csv(out_csv, index=False, encoding="utf-8")
    click.echo(f"Wrote CSV results to: {out_csv}")

    # Write JSON output if requested
    if out_json:
        json_results = _to_json_serializable(results)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(json_results, f, indent=2)
        click.echo(f"Wrote JSON results to: {out_json}")

    click.echo(f"Completed {len(scenario_names)} scenarios")


if __name__ == "__main__":
    main()
