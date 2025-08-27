from __future__ import annotations

import re
from typing import List, Optional

import requests

from .base import SoldComp


def _extract_price(text: str) -> Optional[float]:
    """Extracts a price from a string using regex."""
    # Look for patterns like $123.45, 123.45 USD, etc.
    match = re.search(r"\$?(\d+\.\d{2})", text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            return None
    return None


def _google_search_simple(query: str, max_results: int = 10) -> List[dict]:
    """
    Simple Google search using requests.
    Returns basic search results for price extraction.
    """
    try:
        # Use a simple Google search URL
        search_url = "https://www.google.com/search"
        params = {
            "q": f"{query} price sold",
            "num": max_results,
            "hl": "en",
            "gl": "us",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        # Extract basic results from HTML (simplified)
        results = []
        content = response.text

        # Look for price patterns in the content
        price_patterns = [
            r"\$[\d,]+\.?\d*",
            r"USD [\d,]+\.?\d*",
            r"[\d,]+\.?\d*\s*dollars?",
        ]

        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:max_results]:
                price = _extract_price(match)
                if price and price > 10:  # Filter out very low prices
                    results.append(
                        {
                            "title": f"Google search result for {query}",
                            "snippet": f"Found price: {match}",
                            "price": price,
                            "url": "https://google.com",
                        }
                    )

                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

        return results

    except Exception:
        return []


def fetch_sold_comps_from_google(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 10,
) -> List[SoldComp]:
    """
    Uses Google Search to find potential comparable items.
    This is a low-trust data source, meant for corroboration.
    """
    # Build search query with priority
    if upc:
        search_query = f"{upc} price sold"
    elif asin:
        search_query = f"{asin} price sold"
    elif brand and model:
        search_query = f"{brand} {model} {condition_hint or ''} price sold".strip()
    else:
        search_query = f"{query} {condition_hint or ''} price sold".strip()

    if not search_query:
        return []

    try:
        results = _google_search_simple(search_query, max_results)
    except Exception:
        return []

    comps = []
    for result in results:
        price = result.get("price")
        if price:
            comps.append(
                SoldComp(
                    source="google_search",
                    title=result.get("title", ""),
                    price=price,
                    url=result.get("link"),
                    match_score=0.3,  # Low trust score
                    sold_at=None,  # Cannot determine from search
                    meta={"snippet": result.get("snippet", "")},
                )
            )
    return comps
