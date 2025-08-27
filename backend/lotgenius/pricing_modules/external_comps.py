from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .. import config as _config
from ..datasources import smart_scrapers
from ..datasources.base import SoldComp
from ..evidence import write_evidence  # real ledger
from ..ids import extract_ids


def gather_external_sold_comps(item: Dict[str, Any]) -> List[SoldComp]:
    title = item.get("title") or ""
    brand = item.get("brand")
    model = item.get("model")
    ids = extract_ids(item)
    upc = ids["upc"]  # optional
    asin = ids["asin"] or item.get("asin")
    cond = item.get("condition")
    comps: List[SoldComp] = []
    errors: Dict[str, str] = {}

    # Try eBay scraper if enabled
    if _config.settings.ENABLE_EBAY_SCRAPER and _config.settings.SCRAPER_TOS_ACK:
        try:
            ebay_comps = smart_scrapers.smart_ebay_scraper(
                query=title,
                brand=brand,
                model=model,
                upc=upc,
                asin=asin,
                condition_hint=cond,
                max_results=_config.settings.EXTERNAL_COMPS_MAX_RESULTS,
                days_lookback=_config.settings.EXTERNAL_COMPS_LOOKBACK_DAYS,
            )
            comps.extend(ebay_comps)
        except Exception as e:
            errors["ebay"] = str(e)

    # Try Google Search if enabled
    if _config.settings.ENABLE_GOOGLE_SEARCH_ENRICHMENT:
        try:
            google_comps = smart_scrapers.smart_google_scraper(
                query=title,
                brand=brand,
                model=model,
                upc=upc,
                asin=asin,
                condition_hint=cond,
                max_results=_config.settings.EXTERNAL_COMPS_MAX_RESULTS,
            )
            comps.extend(google_comps)
        except ImportError as e:
            errors["google_search"] = f"import_error: {str(e)}"
        except Exception as e:
            errors["google_search"] = str(e)

    # Try Facebook Marketplace if enabled
    if _config.settings.ENABLE_FB_SCRAPER and _config.settings.SCRAPER_TOS_ACK:
        try:
            facebook_comps = smart_scrapers.smart_facebook_scraper(
                query=title,
                brand=brand,
                model=model,
                upc=upc,
                asin=asin,
                condition_hint=cond,
                max_results=_config.settings.EXTERNAL_COMPS_MAX_RESULTS,
            )
            comps.extend(facebook_comps)
        except Exception as e:
            errors["facebook"] = str(e)

    # Write single consolidated evidence record
    evidence_meta = {
        "num_comps": len(comps),
        "by_source": {
            "ebay": sum(1 for c in comps if c.source in ["ebay", "ebay_mock"]),
            "google_search": sum(
                1 for c in comps if c.source in ["google_search", "google_mock"]
            ),
            "facebook": sum(
                1
                for c in comps
                if c.source in ["facebook_marketplace", "facebook_mock"]
            ),
        },
        "sample": [asdict(c) for c in comps[:8]],
    }

    # Add errors if any occurred
    if errors:
        evidence_meta["errors"] = errors

    write_evidence(
        item,
        "external_comps_summary",
        evidence_meta,
        ok=True,  # Mark as OK even if partial success
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
        "weight_prior": _config.settings.EXTERNAL_COMPS_PRIOR_WEIGHT,
        "recency_days": None,
    }
