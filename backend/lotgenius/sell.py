from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Heuristics are explicit & tunable (JSON-backed)
_DEFAULT_RANK_TO_SALES = {
    "default": {"a": 500.0, "b": -0.80, "min_rank": 1.0, "max_rank": 2_000_000.0}
}

SELL_EVENT_SOURCE = "sell:estimate"


def load_rank_to_sales(path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    if not path:
        return dict(_DEFAULT_RANK_TO_SALES)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(_DEFAULT_RANK_TO_SALES)
    except Exception:
        return dict(_DEFAULT_RANK_TO_SALES)


def _best_rank_from_row(row: pd.Series) -> Optional[float]:
    # scan a few common columns we may have produced earlier
    for k in [
        "keepa_sales_rank_med",
        "keepa_rank_med",
        "keepa_sales_rank_p50",
        "sales_rank_med",
        "sales_rank",
    ]:
        v = row.get(k)
        try:
            val = float(v)
            if val > 0:
                return val
        except Exception:
            pass
    return None


def _offers_from_row(row: pd.Series) -> int:
    v = row.get("keepa_offers_count")
    try:
        i = int(v)
        return i if i > 0 else 1
    except Exception:
        return 1


def _ptm_z(
    list_price: Optional[float],
    mu: Optional[float],
    sigma: Optional[float],
    cv_fallback: float = 0.20,
) -> float:
    if not (isinstance(mu, (int, float)) and mu > 0):
        return 0.0
    if not (isinstance(sigma, (int, float)) and sigma > 0):
        sigma = max(cv_fallback * float(mu), 1e-6)
    lp = float(list_price if list_price is not None else mu)
    return (lp - float(mu)) / float(sigma)


def _daily_sales_from_rank(rank: float, mapping: Dict[str, float]) -> float:
    # power-law: a * rank^b, bounded by rank limits
    a = float(mapping.get("a", 500.0))
    b = float(mapping.get("b", -0.80))
    rmin = float(mapping.get("min_rank", 1.0))
    rmax = float(mapping.get("max_rank", 2_000_000.0))
    r = min(max(rank, rmin), rmax)
    return max(0.0, a * (r**b))


def _hazard_per_item(
    daily_sales_market: float, offers: int, price_factor: float, cap: float = 1.0
) -> float:
    # convert market daily sales to per-item hazard, saturating by offers and price factor
    if offers <= 0:
        offers = 1
    lam = (daily_sales_market / offers) * max(0.0, price_factor)
    return min(float(lam), float(cap))


def _price_factor_from_z(z: float, beta: float = 0.8) -> float:
    # multiplicative discount on hazard as price rises above market; >0 lowers hazard
    # factor = exp(-beta * max(z, 0)) ; cheaper-than-market (z<0) gives >1 up to a soft cap
    if z >= 0:
        return math.exp(-beta * z)
    # modest boost for under-market pricing, capped to avoid extremes
    return min(math.exp(-beta * z), 3.0)


def estimate_sell_p60(
    df_in: pd.DataFrame,
    *,
    days: int = 60,
    list_price_mode: str = "p50",  # one of {"p50","mu","custom"}
    list_price_multiplier: float = 1.0,
    custom_list_price_col: Optional[str] = None,
    rank_to_sales: Optional[Dict[str, Dict[str, float]]] = None,
    beta_price: float = 0.8,
    hazard_cap: float = 1.0,
    cv_fallback: float = 0.20,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Adds columns:
      sell_p60, sell_hazard_daily, sell_ptm_z, sell_rank_used, sell_offers_used
    Emits evidence events (dicts) with inputs & knobs for transparency.
    """
    mapping = rank_to_sales or _DEFAULT_RANK_TO_SALES
    df = df_in.copy()
    for col in [
        "sell_p60",
        "sell_hazard_daily",
        "sell_ptm_z",
        "sell_rank_used",
        "sell_offers_used",
    ]:
        if col not in df.columns:
            df[col] = None

    events: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        mu = row.get("est_price_mu")
        sigma = row.get("est_price_sigma")
        p50 = row.get("est_price_p50") or row.get(
            "est_price_p50"
        )  # tolerate either naming
        # pick list price
        if list_price_mode == "mu":
            base = mu
        elif (
            list_price_mode == "custom"
            and custom_list_price_col
            and custom_list_price_col in df.columns
        ):
            base = row.get(custom_list_price_col)
        else:
            base = p50 or mu
        list_price = (
            (float(base) * float(list_price_multiplier)) if (base is not None) else None
        )

        # features
        rank = _best_rank_from_row(row)
        offers = _offers_from_row(row)
        z = _ptm_z(list_price, mu, sigma, cv_fallback=cv_fallback)
        pf = _price_factor_from_z(z, beta=beta_price)

        # daily market sales
        daily_sales_market = (
            _daily_sales_from_rank(rank, mapping.get("default", {}))
            if rank is not None
            else 0.0
        )
        # hazard per item
        lam = _hazard_per_item(daily_sales_market, offers, pf, cap=hazard_cap)
        # exponential survival -> p(sold <= days) = 1-exp(-λ*days)
        p60 = 1.0 - math.exp(-lam * float(days))
        p60 = min(max(p60, 0.0), 1.0)

        # write columns
        df.at[idx, "sell_p60"] = float(p60)
        df.at[idx, "sell_hazard_daily"] = float(lam)
        df.at[idx, "sell_ptm_z"] = float(z)
        df.at[idx, "sell_rank_used"] = float(rank) if rank is not None else None
        df.at[idx, "sell_offers_used"] = int(offers)

        events.append(
            {
                "row_index": int(idx),
                "sku_local": row.get("sku_local"),
                "source": SELL_EVENT_SOURCE,
                "ok": True,
                "meta": {
                    "days": days,
                    "list_price": list_price,
                    "list_price_mode": list_price_mode,
                    "list_price_multiplier": list_price_multiplier,
                    "rank": rank,
                    "offers": offers,
                    "mu": mu,
                    "sigma": sigma,
                    "ptm_z": z,
                    "price_beta": beta_price,
                    "daily_sales_market": daily_sales_market,
                    "hazard_daily": lam,
                    "rank_to_sales": mapping.get("default", {}),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    return df, events
