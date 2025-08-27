"""Survival model functionality for sell-through estimation."""

from __future__ import annotations

import functools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import settings
from .normalize import condition_bucket
from .sell import _category_key_from_row, _get_seasonality_factor


@functools.lru_cache(maxsize=1)
def _load_survival_alpha_scaling() -> Dict[str, float]:
    """Load survival alpha scaling factors by category."""
    try:
        alpha_file = Path(__file__).parent / "data" / "survival_alpha.example.json"
        if alpha_file.exists():
            with open(alpha_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    # Return default scaling if file not found or error
    return {"default": 1.0}


def _get_alpha_scale_category(row: pd.Series) -> float:
    """Get alpha scaling factor for item based on category."""
    category = _category_key_from_row(row)
    if not category:
        category = "default"

    alpha_scaling = _load_survival_alpha_scaling()
    return float(alpha_scaling.get(category, alpha_scaling.get("default", 1.0)))


def p_sold_within(days: int, alpha: float, beta: float) -> float:
    """
    Compute probability of sale within specified days using log-logistic survival model.

    The log-logistic survival function is:
    S(t) = 1 / (1 + (t/alpha)^beta)

    Therefore, P(sold within t days) = 1 - S(t) = (t/alpha)^beta / (1 + (t/alpha)^beta)

    Args:
        days: Number of days
        alpha: Scale parameter (time to 50% survival)
        beta: Shape parameter (affects hazard curve shape)

    Returns:
        Probability of sale within the specified number of days (0-1)

    Example:
        >>> p_sold_within(60, alpha=45.0, beta=1.5)
        0.7453559924999299
    """
    if days <= 0:
        return 0.0
    if alpha <= 0:
        raise ValueError("Alpha must be positive")
    if beta <= 0:
        raise ValueError("Beta must be positive")

    # Compute (t/alpha)^beta
    t_ratio = float(days) / float(alpha)
    t_ratio_beta = t_ratio ** float(beta)

    # P(sold within t) = (t/alpha)^beta / (1 + (t/alpha)^beta)
    prob = t_ratio_beta / (1.0 + t_ratio_beta)

    return min(max(prob, 0.0), 1.0)


def _compute_implied_hazard(p_sold: float, days: int) -> float:
    """
    Compute implied daily hazard rate from probability and time period.

    From exponential model: P(sold) = 1 - exp(-λ * days)
    Solving for λ: λ = -ln(1 - P(sold)) / days

    Args:
        p_sold: Probability of sale
        days: Time period in days

    Returns:
        Implied daily hazard rate
    """
    if p_sold <= 0:
        return 0.0
    if p_sold >= 1:
        return float("inf")

    # λ = -ln(1 - p) / t
    return -math.log(1.0 - p_sold) / float(days)


def _ptm_z_survival(
    price: Optional[float],
    mu: Optional[float],
    sigma: Optional[float],
    cv_fallback: float = 0.20,
) -> float:
    """
    Compute price-to-market z-score for feature scaling.

    This is identical to the proxy model's _ptm_z function but extracted
    for reuse in survival model features.
    """
    if not (isinstance(mu, (int, float)) and mu > 0):
        return 0.0
    if not (isinstance(sigma, (int, float)) and sigma > 0):
        sigma = max(cv_fallback * float(mu), 1e-6)
    price_val = float(price if price is not None else mu)
    return (price_val - float(mu)) / float(sigma)


def estimate_sell_p60_survival(
    df_in: pd.DataFrame,
    alpha: float,
    beta: float,
    *,
    days: int = 60,
    price_ref_col: str = "est_price_p50",
    cv_fallback: float = 0.20,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Estimate sell-through probabilities using log-logistic survival model.

    Adds columns:
      sell_p60, sell_hazard_daily, sell_ptm_z, sell_alpha_used, sell_beta_used
    Emits evidence events for transparency.

    Args:
        df_in: Input DataFrame with price estimates
        alpha: Base scale parameter for log-logistic model
        beta: Shape parameter for log-logistic model
        days: Time horizon for probability calculation (default: 60)
        price_ref_col: Column to use for reference price (default: 'est_price_p50')
        cv_fallback: Fallback coefficient of variation for missing sigma

    Returns:
        Tuple of (enhanced DataFrame, evidence events list)

    Features:
        - Basic feature scaling: alpha adjusted by price-to-market z-score
        - Alpha scaling: alpha_item = alpha * exp(0.1 * max(z, 0)) for overpriced items
        - Beta remains constant across items (shape parameter)
    """
    df = df_in.copy()

    # Add survival model output columns
    for col in [
        "sell_p60",
        "sell_hazard_daily",
        "sell_ptm_z",
        "sell_alpha_used",
        "sell_beta_used",
        "sell_condition_used",
        "sell_seasonality_factor",
        "sell_alpha_scale_category",
    ]:
        if col not in df.columns:
            df[col] = None

    events: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        # Extract price features
        mu = row.get("est_price_mu")
        sigma = row.get("est_price_sigma")
        ref_price = row.get(price_ref_col) or row.get("est_price_median") or mu

        # Compute price-to-market z-score for feature scaling
        z = _ptm_z_survival(ref_price, mu, sigma, cv_fallback=cv_fallback)

        # Get condition and seasonality adjustments
        condition = condition_bucket(row)
        condition_velocity_factor = settings.CONDITION_VELOCITY_FACTOR.get(
            condition, 1.0
        )
        seasonality_factor = _get_seasonality_factor(row)

        # Get category-based alpha scaling
        alpha_scale_category = _get_alpha_scale_category(row)

        # Feature-based alpha scaling: increase alpha for overpriced items
        # This makes overpriced items sell slower (higher alpha = longer time to sale)
        alpha_scaling = math.exp(0.1 * max(z, 0.0))  # Only penalize overpriced (z > 0)

        # Apply all adjustments to alpha
        # Lower velocity factors (worse condition/seasonality) increase alpha (slower sales)
        # Category scaling directly multiplies alpha (category-specific baselines)
        velocity_adjustment = condition_velocity_factor * seasonality_factor
        alpha_item = (
            alpha
            * alpha_scale_category
            * alpha_scaling
            / max(1e-6, velocity_adjustment)
        )
        beta_item = beta  # Keep beta constant for simplicity

        # Compute survival probability
        p60 = p_sold_within(days, alpha_item, beta_item)

        # Compute implied daily hazard for downstream compatibility
        hazard_daily = _compute_implied_hazard(p60, days)

        # Store results
        df.at[idx, "sell_p60"] = float(p60)
        df.at[idx, "sell_hazard_daily"] = float(hazard_daily)
        df.at[idx, "sell_ptm_z"] = float(z)
        df.at[idx, "sell_alpha_used"] = float(alpha_item)
        df.at[idx, "sell_beta_used"] = float(beta_item)
        df.at[idx, "sell_condition_used"] = condition
        df.at[idx, "sell_seasonality_factor"] = float(seasonality_factor)
        df.at[idx, "sell_alpha_scale_category"] = float(alpha_scale_category)

        # Create evidence event
        events.append(
            {
                "row_index": int(idx),
                "sku_local": row.get("sku_local"),
                "source": "sell:survival",
                "ok": True,
                "meta": {
                    "days": days,
                    "model": "log-logistic",
                    "alpha_base": alpha,
                    "beta_base": beta,
                    "alpha_used": alpha_item,
                    "beta_used": beta_item,
                    "ref_price": ref_price,
                    "price_ref_col": price_ref_col,
                    "mu": mu,
                    "sigma": sigma,
                    "ptm_z": z,
                    "alpha_scaling": alpha_scaling,
                    "condition": condition,
                    "condition_velocity_factor": condition_velocity_factor,
                    "seasonality_factor": seasonality_factor,
                    "alpha_scale_category": alpha_scale_category,
                    "velocity_adjustment": velocity_adjustment,
                    "p60": p60,
                    "hazard_daily": hazard_daily,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    return df, events


def survival_to_hazard(p_sold: float, days: int) -> float:
    """
    Convert survival model probability to daily hazard rate.

    This is a convenience wrapper around _compute_implied_hazard for public use.

    Args:
        p_sold: Probability of sale within time period
        days: Time period in days

    Returns:
        Implied daily hazard rate
    """
    return _compute_implied_hazard(p_sold, days)
