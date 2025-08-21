from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class SoldComp:
    source: str
    title: str
    price: float
    currency: str = "USD"
    condition: str = "Unknown"
    sold_at: Optional[datetime] = None
    url: Optional[str] = None
    id: Optional[str] = None
    match_score: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None


class SoldCompSource(Protocol):
    def fetch_sold_comps(
        self,
        query: str,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        upc: Optional[str] = None,
        asin: Optional[str] = None,
        condition_hint: Optional[str] = None,
        max_results: int = 50,
        days_lookback: int = 180,
    ) -> List[SoldComp]: ...
