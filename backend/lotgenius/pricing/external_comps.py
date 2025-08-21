from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ..config import settings
from ..datasources import ebay_scraper
from ..datasources.base import SoldComp
from ..evidence import write_evidence  # real ledger


def gather_external_sold_comps(item: Dict[str, Any]) -> List[SoldComp]:
    title = item.get("title") or ""
    brand = item.get("brand")
    model = item.get("model")
    upc = item.get("upc") or item.get("ean")
    asin = item.get("asin")
    cond = item.get("condition")
    comps: List[SoldComp] = []

    try:
        if settings.ENABLE_EBAY_SCRAPER and settings.SCRAPER_TOS_ACK:
            comps += ebay_scraper.fetch_sold_comps(
                query=title,
                brand=brand,
                model=model,
                upc=upc,
                asin=asin,
                condition_hint=cond,
                max_results=settings.EXTERNAL_COMPS_MAX_RESULTS,
                days_lookback=settings.EXTERNAL_COMPS_LOOKBACK_DAYS,
            )
    except Exception as e:
        write_evidence(item, "ebay", {"error": str(e)}, ok=False)

    write_evidence(
        item,
        "external_comps_summary",
        {
            "num_comps": len(comps),
            "by_source": {"ebay": sum(1 for c in comps if c.source == "ebay")},
            "sample": [asdict(c) for c in comps[:8]],
        },
        ok=True,
    )
    return comps


def external_comps_estimator(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    comps = gather_external_sold_comps(item)
    usable = [
        c.price
        for c in comps
        if c.price is not None
        and 1.0 <= float(c.price) <= 10000.0
        and (c.match_score or 0) >= 0.5
    ]
    if len(usable) < 3:
        return None
    usable.sort()
    m = (
        usable[len(usable) // 2]
        if len(usable) % 2 == 1
        else (usable[len(usable) // 2 - 1] + usable[len(usable) // 2]) / 2
    )
    return {
        "source": "external_comps",
        "point": m,
        "stdev": max(1.0, m * 0.15),
        "n": len(usable),
        "weight_prior": settings.EXTERNAL_COMPS_PRIOR_WEIGHT,
        "recency_days": None,
    }
