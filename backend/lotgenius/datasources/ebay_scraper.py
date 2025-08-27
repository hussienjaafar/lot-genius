from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import statistics
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from ..cache_metrics import (
    get_cache_stats,
    record_cache_hit,
    record_cache_miss,
    record_cache_store,
    should_emit_metrics,
)
from ..config import settings
from .base import SoldComp
from .external_comps_cache import get_cached_comps, set_cached_comps

_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
]

# eBay scraper result cache
_EBAY_CACHE_PATH = Path("data/cache/ebay_scraper_cache.sqlite")
_EBAY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
_ebay_cache_lock = threading.Lock()


def _ebay_cache_db():
    """Get eBay cache database connection."""
    conn = sqlite3.connect(_EBAY_CACHE_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ebay_cache (
        fingerprint TEXT PRIMARY KEY,
        results TEXT NOT NULL,
        ts INTEGER NOT NULL
    )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ebay_cache_ts ON ebay_cache(ts);")
    return conn


def _generate_query_fingerprint(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 50,
    days_lookback: int = 180,
) -> str:
    """Generate deterministic fingerprint for query parameters."""
    # Normalize parameters to create consistent fingerprint
    normalized_params = {
        "query": query.strip().lower(),
        "brand": (brand or "").strip().lower(),
        "model": (model or "").strip().lower(),
        "upc": (upc or "").strip(),
        "asin": (asin or "").strip(),
        "condition_hint": (condition_hint or "").strip().lower(),
        "max_results": max_results,
        "days_lookback": days_lookback,
    }

    # Create deterministic JSON string
    fingerprint_data = json.dumps(normalized_params, sort_keys=True)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


def _get_cached_ebay_results(
    fingerprint: str, ttl_sec: int
) -> Optional[List[SoldComp]]:
    """Get cached eBay results by fingerprint."""
    with _ebay_cache_lock:
        conn = _ebay_cache_db()
        cur = conn.execute(
            "SELECT results, ts FROM ebay_cache WHERE fingerprint = ?", (fingerprint,)
        )
        row = cur.fetchone()
        conn.close()

    if not row:
        record_cache_miss("ebay")
        return None

    results_json, ts = row
    if int(time.time()) - ts > ttl_sec:
        record_cache_miss("ebay")
        # Clean up expired entry
        _cleanup_expired_ebay_entries(ttl_sec)
        return None

    record_cache_hit("ebay")
    try:
        results_data = json.loads(results_json)
        return [
            SoldComp(
                source=comp.get("source", "ebay"),
                title=comp.get("title", ""),
                price=comp.get("price"),
                condition=comp.get("condition", "Unknown"),
                sold_at=(
                    datetime.fromisoformat(comp["sold_at"])
                    if comp.get("sold_at")
                    else None
                ),
                url=comp.get("url"),
                id=comp.get("id"),
                match_score=comp.get("match_score", 0.0),
                meta=comp.get("meta", {}),
            )
            for comp in results_data
        ]
    except Exception:
        record_cache_miss("ebay")
        return None


def _cache_ebay_results(fingerprint: str, comps: List[SoldComp]) -> None:
    """Cache eBay results by fingerprint."""
    cache_data = [
        {
            "source": comp.source,
            "title": comp.title,
            "price": comp.price,
            "condition": comp.condition,
            "sold_at": comp.sold_at.isoformat() if comp.sold_at else None,
            "url": comp.url,
            "id": comp.id,
            "match_score": comp.match_score,
            "meta": comp.meta,
        }
        for comp in comps
    ]

    with _ebay_cache_lock:
        conn = _ebay_cache_db()
        conn.execute(
            "INSERT OR REPLACE INTO ebay_cache (fingerprint, results, ts) VALUES (?, ?, ?)",
            (fingerprint, json.dumps(cache_data), int(time.time())),
        )
        conn.commit()
        conn.close()

    record_cache_store("ebay")


def _cleanup_expired_ebay_entries(ttl_sec: int) -> None:
    """Clean up expired eBay cache entries."""
    try:
        with _ebay_cache_lock:
            conn = _ebay_cache_db()
            cutoff_time = int(time.time()) - ttl_sec
            cursor = conn.execute("DELETE FROM ebay_cache WHERE ts < ?", (cutoff_time,))
            cursor.rowcount  # We don't need the count, but ruff wants us to acknowledge it
            conn.commit()
            conn.close()
            # Note: We don't record evictions here since they weren't requested entries
    except Exception:
        pass  # Ignore cleanup errors


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
    return {
        "User-Agent": random.choice(_UAS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.google.com/",
    }


def _sold_completed_url(q: str) -> str:
    from requests.utils import quote

    return f"https://www.ebay.com/sch/i.html?_nkw={quote(q)}&LH_Sold=1&LH_Complete=1"


def _parse_price(text: str) -> Optional[float]:
    s = "".join(ch for ch in text if ch.isdigit() or ch in ".")
    try:
        return float(s) if s else None
    except Exception:
        return None


def _build_targeted_query(
    query: str,
    brand: Optional[str],
    model: Optional[str],
    upc: Optional[str],
    asin: Optional[str],
) -> str:
    """
    Build a targeted eBay query with priority-based selection.

    Priority 1: Exact identifier (UPC/ASIN)
    Priority 2: Brand+Model combination
    Priority 3: Filtered title fallback
    """
    # Priority 1: Exact identifier - quote for exact matches
    if upc:
        return f'"{upc}" {brand or ""}'
    elif asin:
        return f'"{asin}" {brand or ""}'

    # Priority 2: Brand+Model - both quoted for exact phrases
    if brand and model:
        return f'"{brand}" "{model}"'

    # Priority 3: Filtered title fallback
    # Strip generic terms (be more specific about whole word matches)
    generic_terms = {
        "bundle",
        "lot",
        "assorted",
        "various",
        "pack",
        "generic",
        "case",
        "piece",
        "damaged",
        "broken",
        "repair",
        "for",
        "parts",
        "wholesale",
        "of",
        "and",
        "the",
        "a",
        "an",
        "with",
    }

    # Normalize and clean the query
    words = query.lower().split()
    # Keep numbers and meaningful words
    filtered_words = []
    for w in words:
        if w.isdigit() or (w not in generic_terms and len(w) > 2):
            filtered_words.append(w)

    if filtered_words:
        filtered_query = " ".join(filtered_words)
        # Quote multi-token phrases
        if len(filtered_words) > 1:
            return f'"{filtered_query}"'
        return filtered_query

    # Fallback to original query if all words were filtered out
    return query


def _title_similarity(a: str, b: str) -> float:
    """
    Calculate title similarity using rapidfuzz token_set_ratio.
    Returns a score between 0.0 and 1.0.
    """
    return fuzz.token_set_ratio(a, b) / 100.0


def _filter_results(
    results: List[SoldComp],
    target_title: str,
    brand: Optional[str],
    model: Optional[str],
    condition_hint: Optional[str],
    days_lookback: int,
    similarity_min: float = 0.70,
) -> Tuple[List[SoldComp], Dict]:
    """
    Filter results for quality: similarity, condition problems, price outliers.

    Returns: (filtered_results, diagnostics)
    """
    diagnostics = {"similarity": 0, "recency": 0, "price": 0, "condition": 0}

    # Build target string for similarity comparison
    if brand and model:
        target_string = f"{brand} {model}"
    else:
        # Use filtered target_title (same generic-term removal as query builder)
        generic_terms = {
            "bundle",
            "lot",
            "assorted",
            "various",
            "pack",
            "generic",
            "case",
            "piece",
            "damaged",
            "broken",
            "repair",
            "for",
            "parts",
            "wholesale",
            "of",
            "and",
            "the",
            "a",
            "an",
            "with",
        }
        words = target_title.lower().split()
        # Keep numbers and meaningful words
        filtered_words = []
        for w in words:
            if w.isdigit() or (w not in generic_terms and len(w) > 2):
                filtered_words.append(w)
        target_string = " ".join(filtered_words) if filtered_words else target_title

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback)
    filtered = []

    for comp in results:
        # Recency filter (already done in original code, but double-check)
        if comp.sold_at and comp.sold_at < cutoff:
            diagnostics["recency"] += 1
            continue

        # Similarity filter
        similarity = _title_similarity(comp.title, target_string)
        if similarity < similarity_min:
            diagnostics["similarity"] += 1
            continue

        # Model presence check - if model is specified, require it in title
        if model and model.lower() not in comp.title.lower():
            diagnostics["similarity"] += 1  # Count as similarity issue
            continue

        # Condition problem filter - avoid "for parts" items unless explicitly wanted
        if condition_hint and condition_hint.lower() not in ["salvage", "for parts"]:
            problem_terms = [
                "for parts",
                "not working",
                "broken",
                "repair-only",
                "repair only",
            ]
            title_lower = comp.title.lower()
            if any(term in title_lower for term in problem_terms):
                diagnostics["condition"] += 1
                continue

        # Add similarity score to comp metadata
        comp.meta = comp.meta or {}
        comp.meta["similarity"] = similarity

        filtered.append(comp)

    # Price outlier detection (only if we have enough samples)
    if len(filtered) >= 5:
        prices = [comp.price for comp in filtered if comp.price is not None]
        if len(prices) >= 5:
            median_price = statistics.median(prices)
            # Use MAD (Median Absolute Deviation) for outlier detection
            mad = statistics.median([abs(p - median_price) for p in prices])

            # Default outlier threshold (can be made configurable)
            k = getattr(settings, "PRICE_OUTLIER_K", 3.5)

            # Filter out price outliers
            outlier_threshold = k * mad if mad > 0 else float("inf")
            price_filtered = []

            for comp in filtered:
                if (
                    comp.price is not None
                    and abs(comp.price - median_price) > outlier_threshold
                ):
                    diagnostics["price"] += 1
                else:
                    price_filtered.append(comp)

            filtered = price_filtered

    # Add quality scores
    for comp in filtered:
        similarity = comp.meta.get("similarity", 0.0)
        # Simple recency weight (newer = higher score)
        if comp.sold_at:
            days_ago = (datetime.now(timezone.utc) - comp.sold_at).days
            recency_weight = max(0.1, 1.0 - (days_ago / days_lookback))
        else:
            recency_weight = 0.5  # Unknown date gets middle score

        quality_score = 0.7 * similarity + 0.3 * recency_weight
        comp.meta["quality_score"] = quality_score
        comp.match_score = quality_score  # Update the main match score too

    return filtered, diagnostics


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

    # Get TTL from environment (default 24 hours)
    ttl_sec = int(os.getenv("EBAY_CACHE_TTL_SEC", "86400"))

    # Generate fingerprint for this query
    fingerprint = _generate_query_fingerprint(
        query, brand, model, upc, asin, condition_hint, max_results, days_lookback
    )

    # Check new fingerprint-based cache first
    cached_comps = _get_cached_ebay_results(fingerprint, ttl_sec)
    if cached_comps is not None:
        # Add cache stats to results if metrics enabled
        if should_emit_metrics():
            for comp in cached_comps:
                comp.meta = comp.meta or {}
                comp.meta["cache_stats"] = get_cache_stats("ebay")
        return cached_comps

    # Fallback: Check old cache system for backward compatibility
    cached_data = get_cached_comps(
        source="ebay",
        title=query,
        brand=brand,
        model=model,
        upc=upc,
        asin=asin,
        condition_hint=condition_hint,
    )

    if cached_data is not None:
        # Reconstruct SoldComp objects from cached data
        return [
            SoldComp(
                source=comp.get("source", "ebay"),
                title=comp.get("title", ""),
                price=comp.get("price"),
                condition=comp.get("condition", "Unknown"),
                sold_at=(
                    datetime.fromisoformat(comp["sold_at"])
                    if comp.get("sold_at")
                    else None
                ),
                url=comp.get("url"),
                id=comp.get("id"),
                match_score=comp.get("match_score", 0.0),
                meta=comp.get("meta", {}),
            )
            for comp in cached_data
        ]

    # Build targeted query using new query builder
    q = _build_targeted_query(query, brand, model, upc, asin)

    try:
        # Use a session for better cookie handling and connection reuse
        with requests.Session() as session:
            # First, visit eBay homepage to establish session
            session.get("https://www.ebay.com", headers=_headers(), timeout=15)
            _sleep_jitter(base=1.0, spread=0.8)  # Longer delay after homepage visit

            # Then make the actual search request
            resp = session.get(_sold_completed_url(q), headers=_headers(), timeout=20)
            resp.raise_for_status()
            _sleep_jitter(base=1.2, spread=1.0)  # Longer delay after search
    except requests.RequestException:
        # On network error, return empty list rather than raising
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select("li.s-item") or soup.select("div.s-item__wrapper")

    # Parse all items first, then filter
    raw_comps: List[SoldComp] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback)

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
                    sold_at = datetime.strptime(txt[-12:], fmt).replace(
                        tzinfo=timezone.utc
                    )
                    break
                except Exception:
                    pass

        # Only apply basic recency cutoff here, more sophisticated filtering below
        if sold_at and sold_at < cutoff:
            continue

        raw_comps.append(
            SoldComp(
                source="ebay",
                title=title[:300],
                price=price,
                condition=(condition_hint or "Unknown"),
                sold_at=sold_at,
                url=url,
                id=None,
                match_score=0.0,  # Will be computed in filtering step
                meta={"raw_price": raw_price, "query": q, "href": url},
            )
        )
        if len(raw_comps) >= max_results * 2:  # Get more candidates for filtering
            break

    # Apply advanced filtering
    similarity_min = getattr(settings, "SCRAPER_SIMILARITY_MIN", 0.70)
    filtered_comps, diagnostics = _filter_results(
        raw_comps, query, brand, model, condition_hint, days_lookback, similarity_min
    )

    # Limit to requested max_results after filtering
    comps = filtered_comps[:max_results]

    # Cache the results using new fingerprint-based cache
    if comps:
        _cache_ebay_results(fingerprint, comps)

        # Also cache in old system for backward compatibility
        cache_data = [
            {
                "source": comp.source,
                "title": comp.title,
                "price": comp.price,
                "condition": comp.condition,
                "sold_at": comp.sold_at.isoformat() if comp.sold_at else None,
                "url": comp.url,
                "id": comp.id,
                "match_score": comp.match_score,
                "meta": comp.meta,
            }
            for comp in comps
        ]
        set_cached_comps(
            source="ebay",
            comps_data=cache_data,
            title=query,
            brand=brand,
            model=model,
            upc=upc,
            asin=asin,
            condition_hint=condition_hint,
        )

        # Add cache stats to results if metrics enabled
        if should_emit_metrics():
            for comp in comps:
                comp.meta = comp.meta or {}
                comp.meta["cache_stats"] = get_cache_stats("ebay")

    return comps
