"""
Production scrapers that use only real data sources.
Returns empty results if real data is unavailable - NO MOCK DATA.
"""

from __future__ import annotations

from typing import List, Optional

from .base import SoldComp

# Mock imports removed - production mode only uses real data


def smart_ebay_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 20,
    days_lookback: int = 180,
) -> List[SoldComp]:
    """
    Smart eBay scraper that tries real scraping first, falls back to mock data.
    """
    results = []

    # First, try the official eBay API
    try:
        from .ebay_api import fetch_sold_comps

        results = fetch_sold_comps(
            query, brand, model, upc, asin, condition_hint, max_results, days_lookback
        )
        if results:
            print(f"✓ eBay API returned {len(results)} results")
            return results
    except Exception as e:
        print(f"eBay API failed: {e}")

    # Fallback to old scraper method
    try:
        from .ebay_scraper import fetch_sold_comps

        results = fetch_sold_comps(
            query, brand, model, upc, asin, condition_hint, max_results, days_lookback
        )
        if results:
            print(f"✓ eBay scraper returned {len(results)} results")
            return results
    except Exception as e:
        print(f"eBay scraper also failed: {e}")

    # NO MOCK DATA - Return empty results if real sources fail
    print("❌ eBay: No real data available - returning empty results")
    return []


def smart_facebook_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 15,
    location: str = "United States",
) -> List[SoldComp]:
    """
    Smart Facebook scraper that tries real scraping first, falls back to mock data.
    """
    results = []

    # Try the real Facebook scraper
    try:
        from .facebook_scraper import fetch_sold_comps_from_facebook

        results = fetch_sold_comps_from_facebook(
            query, brand, model, upc, asin, condition_hint, max_results, location
        )
        if results:
            print(f"✓ Real Facebook scraper returned {len(results)} results")
            return results
    except Exception as e:
        print(f"Real Facebook scraper failed: {e}")

    # NO MOCK DATA - Return empty results if real sources fail
    print("❌ Facebook: No real data available - returning empty results")
    return []


def smart_google_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 10,
) -> List[SoldComp]:
    """
    Smart Google scraper that tries real scraping first, falls back to mock data.
    """
    results = []

    # Try the real Google scraper
    try:
        from .google_search import fetch_sold_comps_from_google

        results = fetch_sold_comps_from_google(
            query, brand, model, upc, asin, condition_hint, max_results
        )
        if results:
            print(f"✓ Real Google scraper returned {len(results)} results")
            return results
    except Exception as e:
        print(f"Real Google scraper failed: {e}")

    # NO MOCK DATA - Return empty results if real sources fail
    print("❌ Google: No real data available - returning empty results")
    return []


def get_all_comparable_data(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results_per_source: int = 10,
) -> List[SoldComp]:
    """
    Get comparable data from all sources (eBay, Facebook, Google).
    This ensures comprehensive pricing data for the optimization engine.
    """
    all_results = []

    print(f"Gathering comparable data for: {query}")

    # Get data from all sources
    ebay_results = smart_ebay_scraper(
        query, brand, model, upc, asin, condition_hint, max_results_per_source
    )
    all_results.extend(ebay_results)

    facebook_results = smart_facebook_scraper(
        query, brand, model, upc, asin, condition_hint, max_results_per_source
    )
    all_results.extend(facebook_results)

    google_results = smart_google_scraper(
        query, brand, model, upc, asin, condition_hint, max_results_per_source
    )
    all_results.extend(google_results)

    print(f"Total comparable data points: {len(all_results)}")
    print(
        f"  eBay: {len(ebay_results)}, Facebook: {len(facebook_results)}, Google: {len(google_results)}"
    )

    return all_results
