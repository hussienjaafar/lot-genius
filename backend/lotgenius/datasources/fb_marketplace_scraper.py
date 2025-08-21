from __future__ import annotations

from typing import List, Optional

from ..config import settings
from .base import SoldComp


def fetch_sold_comps(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 50,
    days_lookback: int = 180,
) -> List[SoldComp]:
    # Stub: inert unless explicitly enabled AND ToS acked.
    if not (settings.SCRAPER_TOS_ACK and settings.ENABLE_FB_SCRAPER):
        return []
    # Intentionally not implemented here (requires Playwright + session). Return [] to remain safe.
    return []
