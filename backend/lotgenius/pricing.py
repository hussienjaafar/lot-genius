from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Reuse EvidenceRecord for consistency
from .resolve import EvidenceRecord


@dataclass
class SourceStat:
    name: str  # e.g., "keepa:new", "keepa:used", "other:*"
    mu: Optional[float]  # point estimate for this source
    cv: Optional[float]  # coefficient of variation (σ / μ)
    n: int  # sample/strength proxy (>=1)
    recency: float  # 0..1
    prior: float  # 0..1 prior weight


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        f = float(x)
        if math.isfinite(f):
            return f
        return None
    except Exception:
        return None


def _clip_pos(x: float) -> float:
    return float(x) if x > 0 else 0.0


def _pctl_normal(mu: float, sigma: float, q: float) -> float:
    # N(0,1) quantiles: 5th≈-1.64485, 50th=0, 95th≈+1.64485
    z = -1.6448536269514729 if q == 0.05 else (0.0 if q == 0.50 else 1.6448536269514729)
    return mu + z * sigma


def _inverse_variance_weight(
    mu: float, cv: float, prior: float, recency: float, n: int
) -> float:
    """
    Weight ∝ (prior × recency × n) / variance, with variance=(cv*mu)^2.
    Guard against cv=0 by flooring.
    """
    cv_eff = max(1e-6, float(cv))
    var = (cv_eff * max(1e-6, mu)) ** 2
    base = prior * max(0.0, recency) * max(1, int(n))
    return base / var


def _offers_to_n(offers: Optional[float]) -> int:
    try:
        if offers is None:
            return 1
        o = int(offers)
        return o if o > 0 else 1
    except Exception:
        return 1


def build_sources_from_row(
    row: pd.Series,
    priors: Dict[str, float],
    cv_fallback: float,
    use_used_for_nonnew: bool,
) -> List[SourceStat]:
    """
    Build zero-or-more SourceStat entries from a row with Keepa stats.
    - If condition is New/Like-New: prefer keepa:new; else prefer keepa:used.
    - If preferred is missing, fall back to the other if present.
    """
    cond = str(row.get("condition") or "").strip().lower()
    # normalized new-ish?
    is_newish = cond in {
        "new",
        "like-new",
        "likenew",
        "open box",
        "open-box",
        "new(other)",
    }

    new_med = _safe_float(row.get("keepa_price_new_med"))
    used_med = _safe_float(row.get("keepa_price_used_med"))
    offers = row.get("keepa_offers_count")
    n_proxy = _offers_to_n(offers)
    recency = 1.0  # placeholder; can be derived from Keepa later

    sources: List[SourceStat] = []
    # Preferred path
    if is_newish and new_med is not None:
        sources.append(
            SourceStat(
                "keepa:new",
                new_med,
                cv_fallback,
                n_proxy,
                recency,
                priors.get("keepa", 0.5),
            )
        )
    elif (not is_newish) and (used_med is not None):
        sources.append(
            SourceStat(
                "keepa:used",
                used_med,
                cv_fallback,
                n_proxy,
                recency,
                priors.get("keepa", 0.5),
            )
        )
    # Fallback path
    elif new_med is not None:
        sources.append(
            SourceStat(
                "keepa:new",
                new_med,
                cv_fallback,
                n_proxy,
                recency,
                priors.get("keepa", 0.5),
            )
        )
    elif used_med is not None:
        sources.append(
            SourceStat(
                "keepa:used",
                used_med,
                cv_fallback,
                n_proxy,
                recency,
                priors.get("keepa", 0.5),
            )
        )

    # TODO: add eBay/other sources later when available
    return sources


def triangulate_price(
    sources: List[SourceStat],
) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
    """
    Inverse-variance weighted μ and σ.
    Returns (mu, sigma, debug_meta). If no sources → (None, None, meta).
    """
    if not sources:
        return None, None, {"note": "no sources"}

    weights = []
    for s in sources:
        if s.mu is None or s.cv is None:
            continue
        w = _inverse_variance_weight(s.mu, s.cv, s.prior, s.recency, s.n)
        weights.append((w, s))
    if not weights:
        return None, None, {"note": "no valid weights"}

    sum_w = sum(w for w, _ in weights)
    mu = sum(w * s.mu for w, s in weights) / sum_w
    # For inverse-variance weighting, σ^2 ≈ 1/sum(w)
    sigma = math.sqrt(1.0 / sum_w)

    meta = {
        "sources": [asdict(s) | {"weight": w} for (w, s) in weights],
        "sum_w": sum_w,
    }
    return mu, sigma, meta


def estimate_prices(
    df_in: pd.DataFrame,
    cv_fallback: float = 0.20,
    priors: Optional[Dict[str, float]] = None,
    use_used_for_nonnew: bool = True,
) -> Tuple[pd.DataFrame, List[EvidenceRecord]]:
    """
    Compute per-row μ, σ and P5/P50/P95. Adds columns:
      est_price_mu, est_price_sigma, est_price_p5, est_price_p50, est_price_p95, est_price_sources
    """
    priors = priors or {"keepa": 0.50, "ebay": 0.35, "other": 0.15}

    df = df_in.copy()
    for col in [
        "est_price_mu",
        "est_price_sigma",
        "est_price_p5",
        "est_price_p50",
        "est_price_p95",
        "est_price_sources",
    ]:
        if col not in df.columns:
            df[col] = None

    ledger: List[EvidenceRecord] = []
    for idx, row in df.iterrows():
        srcs = build_sources_from_row(
            row,
            priors=priors,
            cv_fallback=cv_fallback,
            use_used_for_nonnew=use_used_for_nonnew,
        )
        mu, sigma, meta = triangulate_price(srcs)

        if mu is not None and sigma is not None:
            p5 = _clip_pos(_pctl_normal(mu, sigma, 0.05))
            p50 = _clip_pos(_pctl_normal(mu, sigma, 0.50))
            p95 = _clip_pos(_pctl_normal(mu, sigma, 0.95))

            df.at[idx, "est_price_mu"] = float(mu)
            df.at[idx, "est_price_sigma"] = float(sigma)
            df.at[idx, "est_price_p5"] = float(p5)
            df.at[idx, "est_price_p50"] = float(p50)
            df.at[idx, "est_price_p95"] = float(p95)
            df.at[idx, "est_price_sources"] = json.dumps(
                meta["sources"], ensure_ascii=False
            )
            ok = True
        else:
            ok = False

        # Evidence
        ledger.append(
            EvidenceRecord(
                row_index=int(idx),
                sku_local=(
                    row.get("sku_local")
                    if isinstance(row.get("sku_local"), str)
                    else None
                ),
                upc_ean_asin=(
                    row.get("upc_ean_asin")
                    if isinstance(row.get("upc_ean_asin"), str)
                    else None
                ),
                source="price:estimate",
                ok=ok,
                match_asin=(
                    row.get("asin") if isinstance(row.get("asin"), str) else None
                ),
                cached=None,
                meta={"triangulation": meta},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    return df, ledger
