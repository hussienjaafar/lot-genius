from __future__ import annotations

from typing import Any, Dict


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def extract_stats_compact(keepa_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a compact, serializable dict of price/rank/offer stats.
    We keep this defensive: look for a few conventional keys; otherwise return None fields.
    Expected fixture structure (see tests):
      products[0].stats:
        priceNewMedian, priceUsedMedian, salesRankMedian
      products[0].offers (int)
    """
    out = {
        "price_new_median": None,
        "price_used_median": None,
        "salesrank_median": None,
        "offers_count": None,
    }
    try:
        products = (keepa_payload or {}).get("products") or []
        if not products:
            return out
        p0 = products[0]
        stats = (p0 or {}).get("stats") or {}
        # values are expected in native currency units in the fixture (no cents conversion here)
        out["price_new_median"] = _num(stats.get("priceNewMedian"))
        out["price_used_median"] = _num(stats.get("priceUsedMedian"))
        out["salesrank_median"] = _num(stats.get("salesRankMedian"))
        # offers may be on product root or nested
        out["offers_count"] = p0.get("offers")
        if out["offers_count"] is None:
            out["offers_count"] = (
                stats.get("offers") if isinstance(stats.get("offers"), int) else None
            )
        return out
    except Exception:
        return out
