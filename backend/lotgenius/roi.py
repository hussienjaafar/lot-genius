from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

DEFAULTS = dict(
    horizon_days=60,  # horizon governed upstream by sell_p60 (60d)
    roi_target=1.25,
    risk_threshold=0.80,  # P(ROI >= target)
    sims=2000,
    salvage_frac=0.50,  # salvage as fraction of drawn price if unsold
    marketplace_fee_pct=0.12,  # 12% marketplace fee (sold only)
    payment_fee_pct=0.03,  # 3% payment fee (sold only)
    per_order_fee_fixed=0.40,  # $0.40/order (sold only)
    shipping_per_order=0.0,  # sold only
    packaging_per_order=0.0,  # sold only
    refurb_per_order=0.0,  # sold only
    return_rate=0.08,  # applied to sold orders
    salvage_fee_pct=0.00,  # salvage disposal fee if any
    min_mu_for_item=1e-6,
)


def _valid_items(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["est_price_mu", "est_price_sigma", "sell_p60"]
    keep = df.copy()
    for c in cols:
        if c not in keep.columns:
            keep[c] = np.nan
    # tolerate missing sigma -> infer from mu * cv fallback (20%)
    keep["est_price_sigma"] = keep["est_price_sigma"].fillna(
        keep["est_price_mu"] * 0.20
    )
    # drop items without usable mu
    keep = keep[(keep["est_price_mu"].astype(float) > DEFAULTS["min_mu_for_item"])]
    # missing sell_p60 -> conservative: 0
    keep["sell_p60"] = keep["sell_p60"].fillna(0.0).clip(0.0, 1.0)
    return keep.reset_index(drop=True)


def simulate_lot_outcomes(
    df_in: pd.DataFrame,
    bid: float,
    *,
    sims: int = DEFAULTS["sims"],
    salvage_frac: float = DEFAULTS["salvage_frac"],
    marketplace_fee_pct: float = DEFAULTS["marketplace_fee_pct"],
    payment_fee_pct: float = DEFAULTS["payment_fee_pct"],
    per_order_fee_fixed: float = DEFAULTS["per_order_fee_fixed"],
    shipping_per_order: float = DEFAULTS["shipping_per_order"],
    packaging_per_order: float = DEFAULTS["packaging_per_order"],
    refurb_per_order: float = DEFAULTS["refurb_per_order"],
    return_rate: float = DEFAULTS["return_rate"],
    salvage_fee_pct: float = DEFAULTS["salvage_fee_pct"],
    lot_fixed_cost: float = 0.0,
    seed: Optional[int] = 1337,
) -> Dict[str, Any]:
    """
    Vectorized MC:
      - price ~ Normal(mu, sigma), clipped at 0
      - sold ~ Bernoulli(sell_p60)
      - realized revenue = sold * (price*(1 - mkt - pay) - per_order_fee_fixed - shipping - packaging - refurb) * (1 - return)
      - salvage revenue (unsold) = (1 - sold) * (price * salvage_frac * (1 - salvage_fee_pct))
      - cash_60d = sold_net_revenue (exclude salvage)
      - total_cost = bid  (other per-order costs already netted into revenue)
    Returns arrays and summary stats.
    """
    df = _valid_items(df_in)
    n = df.shape[0]
    if n == 0:
        rng = np.random.default_rng(seed)
        roi = np.zeros(sims)
        zeros_arr = np.zeros(sims)
        return dict(
            sims=int(sims),
            items=int(n),
            bid=float(bid),
            revenue=zeros_arr,
            cash_60d=zeros_arr,
            roi=roi,
            roi_p5=float(np.quantile(roi, 0.05)),
            roi_p50=float(np.quantile(roi, 0.50)),
            roi_p95=float(np.quantile(roi, 0.95)),
            cash_60d_p5=float(np.quantile(zeros_arr, 0.05)),
            cash_60d_p50=float(np.quantile(zeros_arr, 0.50)),
            cash_60d_p95=float(np.quantile(zeros_arr, 0.95)),
            prob_roi_ge_target=None,  # computed by feasible()
        )

    rng = np.random.default_rng(seed)
    mu = df["est_price_mu"].to_numpy(float)
    sigma = df["est_price_sigma"].to_numpy(float)
    p_sell = df["sell_p60"].to_numpy(float)

    # Draw price matrix (sims x n)
    price = rng.normal(loc=mu, scale=sigma, size=(sims, n))
    price = np.clip(price, 0.0, None)

    sold = rng.binomial(1, p_sell, size=(sims, n)).astype(float)
    # Fees on sold items
    fee_pct = marketplace_fee_pct + payment_fee_pct
    per_order_cost = (
        per_order_fee_fixed
        + shipping_per_order
        + packaging_per_order
        + refurb_per_order
    )

    net_sold = sold * (price * (1.0 - fee_pct) - per_order_cost)
    # returns on sold (Bernoulli or expectation); use expectation for speed
    net_sold *= 1.0 - return_rate

    # salvage on unsold items
    salvage = (1.0 - sold) * (price * salvage_frac * (1.0 - salvage_fee_pct))

    revenue = np.maximum(0.0, net_sold) + np.maximum(0.0, salvage)
    cash_60d = np.maximum(0.0, net_sold)  # cash within the horizon excludes salvage

    total_cost = float(bid) + float(lot_fixed_cost)
    revenue_sum = revenue.sum(axis=1)
    cash_sum = cash_60d.sum(axis=1)
    roi = np.divide(
        revenue_sum, total_cost, out=np.zeros_like(revenue_sum), where=(total_cost > 0)
    )

    return dict(
        sims=int(sims),
        items=int(n),
        bid=float(bid),
        revenue=revenue_sum,
        cash_60d=cash_sum,
        roi=roi,
        roi_p5=float(np.quantile(roi, 0.05)),
        roi_p50=float(np.quantile(roi, 0.50)),
        roi_p95=float(np.quantile(roi, 0.95)),
        cash_60d_p5=float(np.quantile(cash_sum, 0.05)),
        cash_60d_p50=float(np.quantile(cash_sum, 0.50)),
        cash_60d_p95=float(np.quantile(cash_sum, 0.95)),
    )


def feasible(
    df: pd.DataFrame,
    bid: float,
    *,
    roi_target: float = DEFAULTS["roi_target"],
    risk_threshold: float = DEFAULTS["risk_threshold"],
    min_cash_60d: Optional[float] = None,
    min_cash_60d_p5: Optional[float] = None,
    **kwargs,
) -> Tuple[bool, Dict[str, Any]]:
    mc = simulate_lot_outcomes(df, bid, **kwargs)
    roi = mc["roi"]
    prob = float((roi >= roi_target).mean())
    cash = float(mc["cash_60d"].mean())
    cash_p5 = float(np.quantile(mc["cash_60d"], 0.05))

    ok = (
        prob >= risk_threshold
        and (True if min_cash_60d is None else (cash >= min_cash_60d))
        and (True if min_cash_60d_p5 is None else (cash_p5 >= min_cash_60d_p5))
    )

    mc["prob_roi_ge_target"] = prob
    mc["expected_cash_60d"] = cash
    mc["cash_60d_p5"] = cash_p5
    mc["meets_constraints"] = bool(ok)
    mc["roi_target"] = float(roi_target)
    mc["risk_threshold"] = float(risk_threshold)
    mc["min_cash_60d"] = None if min_cash_60d is None else float(min_cash_60d)
    mc["min_cash_60d_p5"] = None if min_cash_60d_p5 is None else float(min_cash_60d_p5)
    return ok, mc


def optimize_bid(
    df: pd.DataFrame,
    *,
    lo: float,
    hi: float,
    tol: float = 10.0,  # dollars
    max_iter: int = 32,
    **kwargs,
) -> Dict[str, Any]:
    """Bisection on feasible() to find max bid meeting constraints."""
    best = None
    left = float(lo)
    right = float(hi)
    it = 0
    while (right - left) > tol and it < max_iter:
        mid = float((left + right) / 2.0)
        ok, mc = feasible(df, mid, **kwargs)
        if ok:
            best = mc.copy()
            best["bid"] = mid
            left = mid
        else:
            right = mid
        it += 1
    # Final evaluation at left bound
    if best is None:
        ok, mc = feasible(df, left, **kwargs)
        best = mc.copy()
        best["bid"] = left
    best["iterations"] = it
    best["timestamp"] = datetime.now(timezone.utc).isoformat()
    return best
