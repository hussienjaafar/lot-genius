from __future__ import annotations

from typing import Any, Dict, Optional


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def _to_int(x) -> Optional[int]:
    # Accept ints or digit-like strings, else None
    try:
        if isinstance(x, bool):
            return None
        if isinstance(x, int):
            return x
        if isinstance(x, str) and x.strip().isdigit():
            return int(x.strip())
    except Exception:
        pass
    return None


# NOTE: This is a conservative heuristic for Keepa medians that *might* be reported in cents.
# If both medians look like large, integer-ish values (>=1000, or strongly integer >=200), we divide by 100.
# Prefer false-negatives over false-positives; replace with a strict rule if you standardize units upstream.
def _maybe_cents_to_unit(
    v_new: Optional[float], v_used: Optional[float]
) -> tuple[Optional[float], Optional[float], bool, Optional[str]]:
    """
    Heuristic: Keepa often reports medians in cents.
    If BOTH present and look like cents (large integers or >=100 with 0.99-ish patterns absent), divide by 100.
    We err on the side of not scaling when uncertain.
    """
    scaled = False
    rule = None
    a, b = v_new, v_used

    # Helper to decide if a single value "looks like cents"
    def looks_cents(x: Optional[float]) -> bool:
        if x is None:
            return False
        # integers >= 1000 likely cents; or integers >= 200 are suspicious
        is_int_like = abs(x - int(x)) < 1e-9
        return is_int_like and (x >= 1000 or x >= 200)

    if v_new is not None or v_used is not None:
        # If both exist, both should look like cents to trigger scaling
        if v_new is not None and v_used is not None:
            if looks_cents(v_new) and looks_cents(v_used):
                a = v_new / 100.0
                b = v_used / 100.0
                scaled = True
                rule = "heuristic:int-like>=1000 or >=200 → divide by 100"
        else:
            # If only one exists and it strongly looks like cents
            only = v_new if v_new is not None else v_used
            if looks_cents(only):
                if v_new is not None:
                    a = v_new / 100.0
                if v_used is not None:
                    b = v_used / 100.0
                scaled = True
                rule = "heuristic:int-like>=1000 or >=200 → divide by 100"

    return a, b, scaled, rule


def extract_stats_compact(keepa_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a compact, serializable dict of price/rank/offer stats.
    Fields:
      - price_new_median, price_used_median (currency units; cents auto-normalized)
      - salesrank_median
      - offers_count (int)
      - scaled_from_cents (bool)
      - scale_rule (str|None) - description of scaling applied, if any
    """
    out = {
        "price_new_median": None,
        "price_used_median": None,
        "salesrank_median": None,
        "offers_count": None,
        "scaled_from_cents": False,
        "scale_rule": None,
    }
    try:
        products = (keepa_payload or {}).get("products") or []
        if not products:
            return out
        p0 = products[0] or {}
        stats = p0.get("stats") or {}

        v_new = _num(stats.get("priceNewMedian"))
        v_used = _num(stats.get("priceUsedMedian"))
        v_rank = _num(stats.get("salesRankMedian"))

        # Offers can be on root or in stats; accept int or numeric string, ignore arrays
        offers = p0.get("offers")
        offers = _to_int(offers) if offers is not None else _to_int(stats.get("offers"))

        # Normalize possible cents
        v_new_n, v_used_n, scaled, rule = _maybe_cents_to_unit(v_new, v_used)

        out.update(
            {
                "price_new_median": v_new_n,
                "price_used_median": v_used_n,
                "salesrank_median": v_rank,
                "offers_count": offers,
                "scaled_from_cents": bool(scaled),
                "scale_rule": rule if scaled else None,
            }
        )
        return out
    except Exception:
        return out
