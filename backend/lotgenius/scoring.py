from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _safe_bool(v: Any) -> bool:
    try:
        return bool(v)
    except Exception:
        return False


def product_confidence(signals: Dict[str, Any]) -> float:
    """
    Compute a 0..1 product match confidence using multi-source signals.

    Expected keys in `signals` (all optional):
      - title_similarity: float in [0,1]
      - brand_match: bool
      - model_present: bool
      - price_z: float (abs distance; ~0 good; >=3 poor)
      - sources_count: int distinct corroborating sources (e.g., keepa + comps)
      - recency_days: int days; lower is better
      - high_trust_id: bool (asin/upc/ean present)

    The function is monotone with respect to each factor and deterministic.
    """
    ts = float(signals.get("title_similarity", 0.0) or 0.0)
    ts = _clamp01(ts)

    brand = _safe_bool(signals.get("brand_match"))
    model = _safe_bool(signals.get("model_present"))

    try:
        z = abs(float(signals.get("price_z", 0.0) or 0.0))
    except Exception:
        z = 0.0
    # Map |z| in [0,3+] to [1,0]
    price_score = max(0.0, 1.0 - min(3.0, z) / 3.0)

    try:
        sources = int(signals.get("sources_count", 0) or 0)
    except Exception:
        sources = 0
    # 0 -> 0, 1 -> 0.5, >=2 -> 1.0 then scaled by weight
    sources_score = 0.0 if sources <= 0 else (0.5 if sources == 1 else 1.0)

    try:
        recency_days = int(signals.get("recency_days", 9999) or 9999)
    except Exception:
        recency_days = 9999
    if recency_days <= 30:
        recency_score = 1.0
    elif recency_days <= 90:
        recency_score = 0.6
    elif recency_days <= 180:
        recency_score = 0.3
    else:
        recency_score = 0.0

    high_id = _safe_bool(signals.get("high_trust_id"))

    # Weights sum to <= 1; clamp at the end
    score = 0.0
    score += 0.35 * ts
    score += 0.15 * (1.0 if brand else 0.0)
    score += 0.10 * (1.0 if model else 0.0)
    score += 0.25 * price_score
    score += 0.10 * sources_score
    score += 0.05 * recency_score
    score += 0.05 * (1.0 if high_id else 0.0)

    return _clamp01(score)


def derive_signals_from_item(
    item: Dict[str, Any],
    keepa_blob: Optional[Dict[str, Any]] = None,
    sold_comps: Optional[List[Dict[str, Any]]] = None,
    high_trust_id: bool = False,
) -> Dict[str, Any]:
    """
    Best-effort derivation of product confirmation signals from item + keepa.
    Safe defaults are used when fields are missing.
    """
    keepa_blob = keepa_blob or {}
    sold_comps = sold_comps or []

    title_item = (item.get("title") or "").strip()
    title_keepa = (keepa_blob.get("title") or "").strip()
    title_similarity = 0.0
    if title_item and title_keepa:
        li = title_item.lower()
        lk = title_keepa.lower()
        if li == lk:
            title_similarity = 1.0
        elif li in lk or lk in li:
            title_similarity = 0.75
        else:
            # simple token overlap
            si = set(li.split())
            sk = set(lk.split())
            inter = len(si & sk)
            union = max(1, len(si | sk))
            title_similarity = inter / union

    brand_item = (item.get("brand") or "").strip().lower()
    brand_keepa = (keepa_blob.get("brand") or "").strip().lower()
    brand_match = bool(brand_item and brand_keepa and brand_item == brand_keepa)

    model_present = bool((item.get("model") or "").strip())

    # Price z vs keepa; prefer *_mu and *_sigma if available
    def _get_num(d: Dict[str, Any], keys: List[str]) -> Optional[float]:
        for k in keys:
            v = d.get(k)
            try:
                if v is None:
                    continue
                f = float(v)
                if math.isfinite(f):
                    return f
            except Exception:
                continue
        return None

    est_mu = (
        _get_num(
            item, ["est_price_mu", "keepa_price_mu", "keepa_new_mu", "keepa_used_mu"]
        )
        or 0.0
    )
    est_sigma = (
        _get_num(
            item,
            [
                "est_price_sigma",
                "keepa_price_sigma",
                "keepa_new_sigma",
                "keepa_used_sigma",
            ],
        )
        or 0.0
    )
    baseline = _get_num(keepa_blob, ["mu", "avg", "mean", "buyBoxPrice"]) or est_mu
    baseline_sigma = _get_num(keepa_blob, ["sigma", "std", "stdev"]) or est_sigma
    if baseline_sigma and baseline_sigma > 0:
        price_z = (est_mu - baseline) / baseline_sigma
    else:
        price_z = 0.0

    sources_count = 0
    if keepa_blob:
        sources_count += 1
    if sold_comps:
        sources_count += 1

    # recency from newest comp
    recency_days = 9999
    for c in sold_comps:
        ts = c.get("sold_at") or c.get("sold_ts") or c.get("timestamp") or None
        try:
            if ts is None:
                continue
            import datetime as _dt

            if isinstance(ts, (int, float)):
                dt = _dt.datetime.fromtimestamp(ts)
            else:
                dt = _dt.datetime.fromisoformat(str(ts).replace("Z", ""))
            days = (_dt.datetime.now() - dt).days
            recency_days = min(recency_days, days)
        except Exception:
            continue

    if recency_days == 9999:
        # unknown -> neutral-ish
        recency_days = 181

    return {
        "title_similarity": title_similarity,
        "brand_match": brand_match,
        "model_present": model_present,
        "price_z": price_z,
        "sources_count": sources_count,
        "recency_days": recency_days,
        "high_trust_id": bool(high_trust_id),
    }
