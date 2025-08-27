"""
Mock scrapers that return realistic pricing data for testing and development.
These can be used when real scrapers are blocked or for consistent testing.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .base import SoldComp

# Realistic price data for common items
MOCK_PRICING_DATA = {
    "iphone": {
        "base_price": 400,
        "variance": 0.3,
        "titles": [
            "Apple iPhone 13 128GB Unlocked",
            "iPhone 13 Pro 256GB Space Gray",
            "Apple iPhone 13 Mini Blue",
            "iPhone 13 128GB Pink Unlocked",
            "Apple iPhone 13 Pro Max 512GB",
        ],
    },
    "nintendo": {
        "base_price": 200,
        "variance": 0.4,
        "titles": [
            "Nintendo Switch Console with Joy-Con",
            "Nintendo Switch OLED Model White",
            "Nintendo Switch Lite Coral",
            "Nintendo Switch Gray Console",
            "Nintendo Switch Animal Crossing Edition",
        ],
    },
    "airpods": {
        "base_price": 150,
        "variance": 0.25,
        "titles": [
            "Apple AirPods Pro 2nd Generation",
            "Apple AirPods 3rd Generation",
            "Apple AirPods Pro with MagSafe",
            "Apple AirPods Max Space Gray",
            "Apple AirPods 2nd Generation",
        ],
    },
    "macbook": {
        "base_price": 800,
        "variance": 0.4,
        "titles": [
            "MacBook Air M1 13-inch 256GB",
            "MacBook Pro 14-inch M1 Pro",
            "MacBook Air M2 13-inch Space Gray",
            "MacBook Pro 16-inch M1 Max",
            "MacBook Air 13-inch Intel Core i5",
        ],
    },
    "playstation": {
        "base_price": 350,
        "variance": 0.3,
        "titles": [
            "Sony PlayStation 5 Console",
            "PlayStation 5 Digital Edition",
            "Sony PS5 Disc Version White",
            "PlayStation 5 Bundle with Games",
            "Sony PlayStation 5 God of War Bundle",
        ],
    },
}


def _get_mock_data_for_query(query: str, brand: Optional[str] = None) -> dict:
    """Get appropriate mock data based on query."""
    query_lower = query.lower()
    brand_lower = (brand or "").lower()

    # Try to match by brand first
    if "apple" in brand_lower or "iphone" in query_lower:
        return MOCK_PRICING_DATA["iphone"]
    elif "nintendo" in brand_lower or "switch" in query_lower:
        return MOCK_PRICING_DATA["nintendo"]
    elif "airpods" in query_lower:
        return MOCK_PRICING_DATA["airpods"]
    elif "macbook" in query_lower:
        return MOCK_PRICING_DATA["macbook"]
    elif "playstation" in query_lower or "ps5" in query_lower:
        return MOCK_PRICING_DATA["playstation"]

    # Fallback to generic pricing based on query length/complexity
    return {
        "base_price": random.randint(50, 500),
        "variance": 0.3,
        "titles": [f"Mock item matching '{query}'"],
    }


def _generate_realistic_price(base_price: float, variance: float) -> float:
    """Generate realistic price with some variance."""
    min_price = base_price * (1 - variance)
    max_price = base_price * (1 + variance)
    return round(random.uniform(min_price, max_price), 2)


def _generate_sold_date(days_back_max: int = 180) -> datetime:
    """Generate a realistic sold date within the lookback period."""
    days_back = random.randint(1, days_back_max)
    return datetime.now(timezone.utc) - timedelta(days=days_back)


def mock_ebay_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 20,
    days_lookback: int = 180,
) -> List[SoldComp]:
    """Mock eBay scraper returning realistic data."""
    mock_data = _get_mock_data_for_query(query, brand)

    results = []
    num_results = random.randint(max(1, max_results // 2), max_results)

    for i in range(num_results):
        # Pick a random title or generate one
        if mock_data["titles"]:
            title = random.choice(mock_data["titles"])
        else:
            title = f"Mock eBay listing for {query}"

        # Add condition to title if specified
        if condition_hint:
            title += f" - {condition_hint.title()}"

        price = _generate_realistic_price(
            mock_data["base_price"], mock_data["variance"]
        )
        sold_date = _generate_sold_date(days_lookback)

        # Generate realistic match score based on title similarity
        match_score = random.uniform(0.7, 0.95)

        comp = SoldComp(
            source="ebay_mock",
            title=title,
            price=price,
            condition=condition_hint or "Unknown",
            sold_at=sold_date,
            url=f"https://www.ebay.com/itm/mock-{i}",
            id=f"mock-ebay-{i}",
            match_score=match_score,
            meta={"mock_data": True, "base_query": query, "condition": condition_hint},
        )
        results.append(comp)

    return results


def mock_facebook_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 15,
    location: str = "United States",
) -> List[SoldComp]:
    """Mock Facebook Marketplace scraper returning realistic data."""
    mock_data = _get_mock_data_for_query(query, brand)

    results = []
    num_results = random.randint(max(1, max_results // 2), max_results)

    locations = [
        "New York, NY",
        "Los Angeles, CA",
        "Chicago, IL",
        "Houston, TX",
        "Phoenix, AZ",
    ]

    for i in range(num_results):
        # Facebook listings tend to be slightly lower than eBay
        price = _generate_realistic_price(
            mock_data["base_price"] * 0.9, mock_data["variance"]
        )

        if mock_data["titles"]:
            title = random.choice(mock_data["titles"])
        else:
            title = f"Mock Facebook listing for {query}"

        # Add condition
        if condition_hint:
            title += f" - {condition_hint.title()}"

        comp = SoldComp(
            source="facebook_mock",
            title=title,
            price=price,
            condition=condition_hint or "Unknown",
            sold_at=None,  # Facebook shows current listings
            url=f"https://www.facebook.com/marketplace/item/mock-{i}",
            id=f"mock-facebook-{i}",
            match_score=random.uniform(0.6, 0.85),
            meta={
                "mock_data": True,
                "location": random.choice(locations),
                "base_query": query,
            },
        )
        results.append(comp)

    return results


def mock_google_scraper(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    max_results: int = 10,
) -> List[SoldComp]:
    """Mock Google search scraper returning realistic data."""
    mock_data = _get_mock_data_for_query(query, brand)

    results = []
    num_results = random.randint(2, max_results)  # Google usually returns fewer results

    sources = ["Amazon", "Best Buy", "Walmart", "Target", "Newegg"]

    for i in range(num_results):
        # Google results tend to have wider price variance
        price = _generate_realistic_price(
            mock_data["base_price"], mock_data["variance"] + 0.1
        )

        source_site = random.choice(sources)
        title = f"{source_site} - {query}"
        if condition_hint:
            title += f" {condition_hint}"

        comp = SoldComp(
            source="google_mock",
            title=title,
            price=price,
            condition=condition_hint or "Unknown",
            sold_at=None,
            url=f"https://www.google.com/search?q={query.replace(' ', '+')}",
            id=f"mock-google-{i}",
            match_score=random.uniform(0.3, 0.6),  # Lower trust score
            meta={"mock_data": True, "source_site": source_site, "base_query": query},
        )
        results.append(comp)

    return results


# For easy integration, provide functions with the same signatures as real scrapers
def fetch_sold_comps_ebay_mock(*args, **kwargs) -> List[SoldComp]:
    """Mock version of eBay scraper."""
    return mock_ebay_scraper(*args, **kwargs)


def fetch_sold_comps_facebook_mock(*args, **kwargs) -> List[SoldComp]:
    """Mock version of Facebook scraper."""
    return mock_facebook_scraper(*args, **kwargs)


def fetch_sold_comps_google_mock(*args, **kwargs) -> List[SoldComp]:
    """Mock version of Google scraper."""
    return mock_google_scraper(*args, **kwargs)
