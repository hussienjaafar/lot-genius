from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import settings
from .base import SoldComp

_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
]


def _guard_enabled() -> None:
    if not settings.SCRAPER_TOS_ACK:
        raise RuntimeError(
            "Scraping disabled: set SCRAPER_TOS_ACK=true after ToS/robots review."
        )
    if not settings.ENABLE_EBAY_SCRAPER:
        raise RuntimeError(
            "eBay scraper disabled: set ENABLE_EBAY_SCRAPER=true to enable."
        )


def _sleep_jitter(base=0.8, spread=0.6):
    time.sleep(base + random.random() * spread)


def _headers():
    return {"User-Agent": random.choice(_UAS), "Accept-Language": "en-US,en;q=0.9"}


def _sold_completed_url(q: str) -> str:
    from requests.utils import quote

    return f"https://www.ebay.com/sch/i.html?_nkw={quote(q)}&LH_Sold=1&LH_Complete=1"


def _parse_price(text: str) -> Optional[float]:
    s = "".join(ch for ch in text if ch.isdigit() or ch in ".")
    try:
        return float(s) if s else None
    except Exception:
        return None


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
    _guard_enabled()
    q_parts = [p for p in (query, brand, model, upc, asin) if p]
    q = " ".join(q_parts) or query

    resp = requests.get(_sold_completed_url(q), headers=_headers(), timeout=20)
    resp.raise_for_status()
    _sleep_jitter()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select("li.s-item") or soup.select("div.s-item__wrapper")

    comps: List[SoldComp] = []
    cutoff = datetime.utcnow() - timedelta(days=days_lookback)

    for el in items:
        title_el = el.select_one(".s-item__title")
        price_el = el.select_one(".s-item__price")
        link_el = el.select_one("a.s-item__link")
        date_el = el.select_one(".s-item__ended-date, .s-item__title--tagblock span")

        title = title_el.get_text(strip=True) if title_el else None
        raw_price = price_el.get_text(strip=True) if price_el else None
        price = _parse_price(raw_price or "")
        url = link_el.get("href") if link_el else None
        if not title or not price:
            continue

        sold_at = None
        if date_el:
            txt = date_el.get_text(" ", strip=True)
            for fmt in ("%b %d, %Y", "%b %d %Y"):
                try:
                    sold_at = datetime.strptime(txt[-12:], fmt)
                    break
                except Exception:
                    pass

        if sold_at and sold_at < cutoff:
            continue

        q_tokens = set(t.lower() for t in q_parts)
        title_tokens = set(title.lower().split())
        match = (
            len(q_tokens & title_tokens) / max(1, len(q_tokens)) if q_tokens else 0.0
        )

        comps.append(
            SoldComp(
                source="ebay",
                title=title[:300],
                price=price,
                condition=(condition_hint or "Unknown"),
                sold_at=sold_at,
                url=url,
                id=None,
                match_score=min(1.0, match),
                meta={"raw_price": raw_price, "query": q, "href": url},
            )
        )
        if len(comps) >= max_results:
            break

    return comps
