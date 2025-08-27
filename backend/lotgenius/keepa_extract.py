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
                rule = "heuristic:int-like>=1000 or >=200 -> divide by 100"
        else:
            # If only one exists and it strongly looks like cents
            only = v_new if v_new is not None else v_used
            if looks_cents(only):
                if v_new is not None:
                    a = v_new / 100.0
                if v_used is not None:
                    b = v_used / 100.0
                scaled = True
                rule = "heuristic:int-like>=1000 or >=200 -> divide by 100"

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
        # Navigate to first product in response
        products = (keepa_payload or {}).get("data", {}).get("products") or []
        if not products:
            return out
        p0 = products[0] or {}
        stats = p0.get("stats") or {}

        # Extract pricing data from multiple sources for robustness
        v_new = None
        v_used = None

        # Priority 1: Current Amazon price (most reliable for liquidation)
        current_data = stats.get("current")
        if current_data and len(current_data) > 1 and current_data[1] != -1:
            v_new = _num(current_data[1] / 100)  # Index 1 = current Amazon price

        # Priority 2: Buy box price (if positive - negative values are status codes)
        if not v_new:
            buybox_price = stats.get("buyBoxPrice")
            if buybox_price and buybox_price > 0:  # Must be positive price
                v_new = _num(buybox_price / 100)

        # Priority 3: 30-day Amazon average for stability
        if not v_new:
            avg30_data = stats.get("avg30")
            if avg30_data and len(avg30_data) > 0 and avg30_data[0] != -1:
                v_new = _num(avg30_data[0] / 100)  # Index 0 = Amazon average

        # Priority 4: Competitive price threshold as fallback
        if not v_new:
            competitive_price = p0.get("competitivePriceThreshold")
            if competitive_price and competitive_price > 0:  # Must be positive
                v_new = _num(competitive_price / 100)

        # Extract used pricing from CSV price tracks (Track 2 = Used prices)
        csv_data = p0.get("csv", [])
        if len(csv_data) >= 3:  # Ensure we have used price track
            used_track = csv_data[2]  # Track 2 = Used prices
            if isinstance(used_track, list) and len(used_track) >= 2:
                # Get recent used price (last non-null value)
                for i in range(
                    len(used_track) - 1, 0, -2
                ):  # Walk backwards through prices
                    if used_track[i] != -1:
                        v_used = _num(used_track[i] / 100)
                        break

        # Sales rank extraction (multiple sources)
        v_rank = None

        # Method 1: Current sales rank from current data (index 3 typically)
        if current_data and len(current_data) > 3 and current_data[3] != -1:
            v_rank = _to_int(current_data[3])

        # Method 2: Sales rank from salesRanks field
        if not v_rank and "salesRanks" in p0 and p0["salesRanks"]:
            sales_ranks = p0["salesRanks"]
            if isinstance(sales_ranks, list) and sales_ranks:
                for rank in sales_ranks:
                    if rank and rank != -1:
                        v_rank = _to_int(rank)
                        break

        # Offers count - use totalOfferCount directly
        offers = _to_int(stats.get("totalOfferCount"))

        # For liquidation, we don't need the complex cents normalization
        # Just ensure reasonable price ranges
        v_new_n = v_new
        v_used_n = v_used
        scaled = False
        rule = "direct_extraction"

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
