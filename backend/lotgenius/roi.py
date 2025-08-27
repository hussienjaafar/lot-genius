from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import settings
from .evidence import filter_items_by_evidence_gate, mark_items_as_upside


def _var_cvar(values: np.ndarray, alpha: float):
    """Compute Value at Risk (VaR) and Conditional Value at Risk (CVaR)."""
    # values are ROI (e.g., 1.0 = breakeven); we measure the shortfall
    q = np.quantile(values, alpha)
    tail = values[values <= q]
    cvar = tail.mean() if tail.size else q
    return float(q), float(cvar)


DEFAULTS = dict(
    horizon_days=settings.SELLTHROUGH_HORIZON_DAYS,  # horizon governed upstream by sell_p60
    roi_target=settings.MIN_ROI_TARGET,
    risk_threshold=settings.RISK_THRESHOLD,  # P(ROI >= target)
    sims=2000,
    salvage_frac=settings.CLEARANCE_VALUE_AT_HORIZON,  # salvage as fraction of drawn price if unsold
    marketplace_fee_pct=0.12,  # 12% marketplace fee (sold only)
    payment_fee_pct=0.03,  # 3% payment fee (sold only)
    per_order_fee_fixed=0.40,  # $0.40/order (sold only)
    shipping_per_order=0.0,  # sold only
    packaging_per_order=0.0,  # sold only
    refurb_per_order=0.0,  # sold only
    return_rate=0.08,  # applied to sold orders
    salvage_fee_pct=0.00,  # salvage disposal fee if any
    min_mu_for_item=1e-6,
    throughput_mins_per_unit=None,  # use settings if None
    capacity_mins_per_day=None,  # use settings if None
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


def apply_evidence_gate_to_items(
    df: pd.DataFrame, evidence_ledger: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Apply Two-Source Rule evidence gating before ROI calculations.

    Items failing evidence gate are excluded from core ROI and marked as upside.

    Args:
        df: DataFrame of items to process
        evidence_ledger: Evidence records for items

    Returns:
        Dict with core_items, upside_items, and summary stats
    """
    if df.empty:
        return {
            "core_items": pd.DataFrame(),
            "upside_items": pd.DataFrame(),
            "evidence_summary": {
                "total_items": 0,
                "core_count": 0,
                "upside_count": 0,
                "gate_pass_rate": 0.0,
            },
        }

    # Apply evidence gate filter
    core_items, failed_items = filter_items_by_evidence_gate(df, evidence_ledger)

    # Mark failed items as upside opportunities
    upside_items = (
        mark_items_as_upside(failed_items) if len(failed_items) > 0 else pd.DataFrame()
    )

    # Create summary statistics
    total_items = len(df)
    core_count = len(core_items)
    upside_count = len(upside_items)
    gate_pass_rate = core_count / total_items if total_items > 0 else 0.0

    evidence_summary = {
        "total_items": total_items,
        "core_count": core_count,
        "upside_count": upside_count,
        "gate_pass_rate": gate_pass_rate,
        "core_percentage": gate_pass_rate * 100,
        "upside_percentage": (
            (upside_count / total_items * 100) if total_items > 0 else 0.0
        ),
    }

    return {
        "core_items": core_items,
        "upside_items": upside_items,
        "evidence_summary": evidence_summary,
    }


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
    # Manifest risk knobs
    defect_rate: float = 0.0,
    missing_rate: float = 0.0,
    grade_mismatch_rate: float = 0.0,
    defect_recovery_frac: float = 0.5,
    missing_recovery_frac: float = 0.0,
    mismatch_discount_frac: float = 0.2,
    lot_fixed_cost: float = 0.0,
    # Ops + storage costs
    ops_cost_per_min: float = 0.0,
    storage_cost_per_unit_per_day: float = 0.0,
    seed: Optional[int] = 1337,
    evidence_ledger: Optional[List[Dict[str, Any]]] = None,
    apply_evidence_gate: bool = False,
) -> Dict[str, Any]:
    """
    Vectorized MC simulation with optional Two-Source Rule evidence gating.

    When apply_evidence_gate=True:
      - Items failing evidence gate are excluded from core ROI
      - Failed items are tracked as upside opportunities
      - Core ROI calculations use only evidence-gated items

    Simulation:
      - price ~ Normal(mu, sigma), clipped at 0
      - sold ~ Bernoulli(sell_p60)
      - realized revenue = sold * (price*(1 - mkt - pay) - per_order_fee_fixed - shipping - packaging - refurb) * (1 - return)
      - salvage revenue (unsold) = (1 - sold) * (price * salvage_frac * (1 - salvage_fee_pct))
      - cash_60d = sold_net_revenue (exclude salvage)
      - total_cost = bid  (other per-order costs already netted into revenue)
    Returns arrays, summary stats, and evidence gate results.
    """
    # Apply evidence gating if requested
    evidence_gate_result = None
    if apply_evidence_gate:
        evidence_gate_result = apply_evidence_gate_to_items(df_in, evidence_ledger)
        df = _valid_items(evidence_gate_result["core_items"])
    else:
        df = _valid_items(df_in)
    n = df.shape[0]
    if n == 0:
        rng = np.random.default_rng(seed)
        roi = np.zeros(sims)
        zeros_arr = np.zeros(sims)
        result = dict(
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
            payout_lag_days=int(settings.PAYOUT_LAG_DAYS),
        )
        if evidence_gate_result:
            result["evidence_gate"] = evidence_gate_result
        return result

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

    # Apply manifest risk adjustments on sold revenue (simulate per item per sim)
    if defect_rate > 0.0 or missing_rate > 0.0 or grade_mismatch_rate > 0.0:
        # Draw Bernoulli masks
        defect_mask = (
            rng.binomial(1, min(max(defect_rate, 0.0), 1.0), size=(sims, n)).astype(
                float
            )
            if defect_rate > 0.0
            else np.zeros((sims, n), dtype=float)
        )
        missing_mask = (
            rng.binomial(1, min(max(missing_rate, 0.0), 1.0), size=(sims, n)).astype(
                float
            )
            if missing_rate > 0.0
            else np.zeros((sims, n), dtype=float)
        )
        mismatch_mask = (
            rng.binomial(
                1, min(max(grade_mismatch_rate, 0.0), 1.0), size=(sims, n)
            ).astype(float)
            if grade_mismatch_rate > 0.0
            else np.zeros((sims, n), dtype=float)
        )
        # Missing: drop revenue, optionally recover a fraction
        if missing_rate > 0.0:
            net_sold = (
                net_sold * (1.0 - missing_mask)
                + net_sold * missing_recovery_frac * missing_mask
            )
        # Defect: recover only a fraction of revenue
        if defect_rate > 0.0:
            net_sold = (
                net_sold * (1.0 - defect_mask)
                + net_sold * defect_recovery_frac * defect_mask
            )
        # Grade mismatch: discount revenue by fraction
        if grade_mismatch_rate > 0.0 and mismatch_discount_frac != 0.0:
            net_sold = net_sold * (1.0 - mismatch_mask * mismatch_discount_frac)

    # Apply payout lag to cash within horizon
    H = settings.SELLTHROUGH_HORIZON_DAYS
    L = settings.PAYOUT_LAG_DAYS
    eps = 1e-9

    if H <= L:
        # If payout lag >= horizon, no cash received within horizon
        payout_fractions = np.zeros(n)
    else:
        # Compute payout fractions per item based on hazard rates
        payout_fractions = np.zeros(n)
        for i in range(n):
            p60_i = max(
                0.0, min(1.0, p_sell[i])
            )  # Clip to [0,1], always needed for payout fraction

            # Prefer explicit sell_hazard_daily if available
            if (
                "sell_hazard_daily" in df.columns
                and pd.notna(df.iloc[i]["sell_hazard_daily"])
                and df.iloc[i]["sell_hazard_daily"] > 0
            ):
                lambda_i = float(df.iloc[i]["sell_hazard_daily"])
            else:
                # Back-solve from sell_p60
                if p60_i < eps:
                    lambda_i = 0.0
                else:
                    lambda_i = -np.log(max(1.0 - p60_i, eps)) / H

            # Compute payout fraction: fraction of sold items that get paid within horizon
            if p60_i < eps:
                f_i = 0.0
            else:
                f_i = (1.0 - np.exp(-lambda_i * (H - L))) / max(p60_i, eps)
                f_i = max(0.0, min(1.0, f_i))  # Clip to [0,1]

            payout_fractions[i] = f_i

    # Apply payout lag to net_sold cash (broadcasting across simulations)
    net_sold_with_lag = net_sold * payout_fractions[np.newaxis, :]  # Shape: (sims, n)

    revenue = np.maximum(0.0, net_sold) + np.maximum(0.0, salvage)
    cash_60d = np.maximum(
        0.0, net_sold_with_lag
    )  # cash within the horizon with payout lag

    # Compute fixed ops + storage costs (not stochastic)
    # Ops minutes per unit (column override else settings)
    if "mins_per_unit" in df.columns:
        per_unit_mins = (
            df["mins_per_unit"]
            .fillna(settings.THROUGHPUT_MINS_PER_UNIT)
            .astype(float)
            .to_numpy()
        )
    else:
        per_unit_mins = np.full(
            n, float(settings.THROUGHPUT_MINS_PER_UNIT), dtype=float
        )
    if "quantity" in df.columns:
        quantities = df["quantity"].fillna(1).astype(float).to_numpy()
    else:
        quantities = np.ones(n, dtype=float)

    total_minutes = float((per_unit_mins * quantities).sum())
    ops_cost_total = (
        float(ops_cost_per_min) * total_minutes if ops_cost_per_min else 0.0
    )

    # Storage expected holding days per item using hazard; cap at horizon
    H = settings.SELLTHROUGH_HORIZON_DAYS
    # Reuse lambda derivation logic from payout fraction block
    lambdas = np.zeros(n, dtype=float)
    for i in range(n):
        # Prefer explicit sell_hazard_daily if available and positive
        if (
            "sell_hazard_daily" in df.columns
            and pd.notna(df.iloc[i]["sell_hazard_daily"])
            and df.iloc[i]["sell_hazard_daily"] > 0
        ):
            lambdas[i] = float(df.iloc[i]["sell_hazard_daily"]) or 0.0
        else:
            p60_i = float(p_sell[i])
            if p60_i <= 0.0:
                lambdas[i] = 0.0
            else:
                lambdas[i] = -np.log(max(1.0 - p60_i, 1e-9)) / H
    expected_days = np.where(lambdas > 0.0, 1.0 / lambdas, float(H))
    expected_days = np.minimum(expected_days, float(H))
    storage_cost_total = (
        float(storage_cost_per_unit_per_day) * float((expected_days * quantities).sum())
        if storage_cost_per_unit_per_day
        else 0.0
    )

    # Aggregate simulation arrays then subtract fixed costs
    total_cost = float(bid) + float(lot_fixed_cost)
    revenue_sum = revenue.sum(axis=1) - ops_cost_total - storage_cost_total
    cash_sum = cash_60d.sum(axis=1) - ops_cost_total - storage_cost_total
    roi = np.divide(
        revenue_sum, total_cost, out=np.zeros_like(revenue_sum), where=(total_cost > 0)
    )

    # Add VaR/CVaR computation
    alpha = settings.VAR_ALPHA
    var_a, cvar_a = _var_cvar(roi, alpha)

    result = dict(
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
        var_alpha=alpha,
        roi_var=var_a,
        roi_cvar=cvar_a,
        payout_lag_days=int(settings.PAYOUT_LAG_DAYS),
        ops_cost_total=float(ops_cost_total),
        storage_cost_total=float(storage_cost_total),
    )
    if evidence_gate_result:
        result["evidence_gate"] = evidence_gate_result
    return result


def feasible(
    df: pd.DataFrame,
    bid: float,
    *,
    roi_target: float = DEFAULTS["roi_target"],
    risk_threshold: float = DEFAULTS["risk_threshold"],
    throughput_mins_per_unit: Optional[float] = DEFAULTS["throughput_mins_per_unit"],
    capacity_mins_per_day: Optional[float] = DEFAULTS["capacity_mins_per_day"],
    min_cash_60d: Optional[float] = None,
    min_cash_60d_p5: Optional[float] = None,
    **kwargs,
) -> Tuple[bool, Dict[str, Any]]:
    mc = simulate_lot_outcomes(df, bid, **kwargs)
    roi = mc["roi"]
    prob = float((roi >= roi_target).mean())
    cash = float(mc["cash_60d"].mean())
    cash_p5 = float(np.quantile(mc["cash_60d"], 0.05))

    # Throughput capacity check
    tp_mins_per_unit = (
        float(throughput_mins_per_unit)
        if throughput_mins_per_unit is not None
        else float(settings.THROUGHPUT_MINS_PER_UNIT)
    )
    cap_mins_per_day = (
        float(capacity_mins_per_day)
        if capacity_mins_per_day is not None
        else float(settings.THROUGHPUT_CAPACITY_MINS_PER_DAY)
    )
    # Allow per-row override via column 'mins_per_unit'
    if "mins_per_unit" in df.columns:
        per_unit = df["mins_per_unit"].fillna(tp_mins_per_unit).astype(float)
        if "quantity" in df.columns:
            quantities = df["quantity"].fillna(1).astype(float)
        else:
            quantities = pd.Series([1.0] * len(df))
        total_minutes = float((per_unit * quantities).sum())
    else:
        if "quantity" in df.columns:
            quantities = df["quantity"].fillna(1).astype(float)
        else:
            quantities = pd.Series([1.0] * len(df))
        total_minutes = float(quantities.sum() * tp_mins_per_unit)
    available_minutes = float(cap_mins_per_day * settings.SELLTHROUGH_HORIZON_DAYS)
    throughput_ok = bool(total_minutes <= available_minutes)

    ok = (
        prob >= risk_threshold
        and (True if min_cash_60d is None else (cash >= min_cash_60d))
        and (True if min_cash_60d_p5 is None else (cash_p5 >= min_cash_60d_p5))
        and throughput_ok
    )

    mc["prob_roi_ge_target"] = prob
    mc["expected_cash_60d"] = cash
    mc["cash_60d_p5"] = cash_p5
    mc["meets_constraints"] = bool(ok)
    mc["roi_target"] = float(roi_target)
    mc["risk_threshold"] = float(risk_threshold)
    mc["min_cash_60d"] = None if min_cash_60d is None else float(min_cash_60d)
    mc["min_cash_60d_p5"] = None if min_cash_60d_p5 is None else float(min_cash_60d_p5)
    mc["throughput"] = {
        "mins_per_unit": tp_mins_per_unit,
        "capacity_mins_per_day": cap_mins_per_day,
        "total_minutes_required": total_minutes,
        "available_minutes": available_minutes,
        "throughput_ok": throughput_ok,
    }
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
