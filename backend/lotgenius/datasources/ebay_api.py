"""
Modern eBay API integration using official eBay Finding & Shopping APIs.
Much more reliable than scraping and provides better data quality.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from ..config import settings
from .base import SoldComp


class EbayAPIClient:
    """Official eBay API client for finding sold listings."""

    def __init__(self, app_id: str = None, oauth_token: str = None):
        self.app_id = app_id
        self.oauth_token = oauth_token
        # Detect environment from credentials/token
        is_sandbox = (app_id and "SBX" in app_id) or (
            oauth_token and "p^1" in oauth_token
        )

        if is_sandbox:
            self.base_url = (
                "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
            )
            self.shopping_url = "https://open.sandbox.ebay.com/shopping"
            self.api_v1_url = "https://api.sandbox.ebay.com/buy/browse/v1"
            print("Using eBay SANDBOX environment")
        else:
            self.base_url = "https://svcs.ebay.com/services/search/FindingService/v1"
            self.shopping_url = "https://open.api.ebay.com/shopping"
            self.api_v1_url = "https://api.ebay.com/buy/browse/v1"
            print("Using eBay PRODUCTION environment")

    def _make_request(self, params: dict, use_oauth: bool = True) -> dict:
        """Make authenticated request to eBay API."""

        if use_oauth and self.oauth_token:
            # Use OAuth token with modern API
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",  # US marketplace
            }
            url = self.api_v1_url
        else:
            # Fallback to legacy API with App ID
            headers = {
                "X-EBAY-SOA-SERVICE-VERSION": "1.13.0",
                "X-EBAY-SOA-SECURITY-APPNAME": self.app_id,
                "X-EBAY-SOA-REQUEST-DATA-FORMAT": "JSON",
                "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "JSON",
            }
            url = self.base_url

        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"eBay API request failed: {e}")
            return {}

    def search_sold_listings(
        self,
        query: str,
        category_id: Optional[str] = None,
        max_results: int = 50,
        days_back: int = 90,
    ) -> List[Dict[str, Any]]:
        """Search for completed/sold listings on eBay."""

        params = {
            "OPERATION-NAME": "findCompletedItems",
            "RESPONSE-DATA-FORMAT": "JSON",
            "keywords": query,
            "paginationInput.entriesPerPage": min(max_results, 100),
            "sortOrder": "EndTimeSoonest",
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
            "itemFilter(1).name": "EndTimeFrom",
            "itemFilter(1).value": f"{days_back}",
        }

        if category_id:
            params["categoryId"] = category_id

        return self._make_request(
            params, use_oauth=False
        )  # Legacy API for sold listings

    def search_items_oauth(
        self,
        query: str,
        category_id: Optional[str] = None,
        max_results: int = 50,
        condition_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search current listings using OAuth token (eBay Browse API)."""

        if not self.oauth_token:
            print("OAuth token required for Browse API")
            return []

        # Build search parameters for Browse API
        params = {
            "q": query,
            "limit": min(max_results, 200),
            "sort": "price",  # Sort by price for consistency
        }

        if category_id:
            params["category_ids"] = category_id

        if condition_filter:
            params["filter"] = f"conditions:{condition_filter}"

        try:
            # Use Browse API search endpoint
            search_url = f"{self.api_v1_url}/item_summary/search"
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            }
            response = requests.get(
                search_url, params=params, headers=headers, timeout=15
            )
            response.raise_for_status()
            return response.json().get("itemSummaries", [])

            # eBay Browse API response structure
            items = response.get("itemSummaries", [])
            return items

        except Exception as e:
            print(f"eBay Browse API search failed: {e}")
            return []

    def get_item_details(self, item_id: str) -> dict:
        """Get detailed information for a specific eBay item."""
        headers = {
            "X-EBAY-SOA-SERVICE-VERSION": "1.13.0",
            "X-EBAY-SOA-SECURITY-APPNAME": self.app_id,
            "X-EBAY-SOA-REQUEST-DATA-FORMAT": "JSON",
            "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "JSON",
        }

        params = {
            "callname": "GetSingleItem",
            "responseencoding": "JSON",
            "ItemID": item_id,
            "IncludeSelector": "Details,Description,ItemSpecifics",
        }

        try:
            response = requests.get(
                self.shopping_url, params=params, headers=headers, timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"eBay item details failed: {e}")
            return {}


def calculate_similarity_score(item_data: dict, search_terms: dict) -> float:
    """
    ML-style similarity scoring for eBay listings.
    Uses multiple signals to determine how well a listing matches our target item.
    """
    score = 0.0
    max_score = 0.0

    # Title similarity (most important - 40% weight)
    title = item_data.get("title", "").lower()
    search_title = search_terms.get("title", "").lower()
    search_brand = search_terms.get("brand", "").lower()
    search_model = search_terms.get("model", "").lower()

    if search_title:
        # Simple word overlap scoring
        search_words = set(search_title.split())
        title_words = set(title.split())
        if search_words and title_words:
            overlap = len(search_words & title_words) / len(search_words)
            score += overlap * 0.4
        max_score += 0.4

    # Brand match (25% weight)
    if search_brand:
        brand_match = 1.0 if search_brand in title else 0.0
        score += brand_match * 0.25
        max_score += 0.25

    # Model match (20% weight)
    if search_model:
        model_match = 1.0 if search_model in title else 0.0
        score += model_match * 0.20
        max_score += 0.20

    # Category relevance (10% weight)
    category = item_data.get("primaryCategory", {}).get("categoryName", "").lower()
    expected_categories = {
        "electronics": ["electronics", "computers", "cell phones", "video games"],
        "clothing": ["clothing", "shoes", "accessories"],
        "home": ["home", "garden", "appliances", "tools"],
    }

    item_category = search_terms.get("category", "").lower()
    if item_category in expected_categories:
        for cat in expected_categories[item_category]:
            if cat in category:
                score += 0.10
                break
        max_score += 0.10

    # Price reasonableness (5% weight)
    # Items priced too high or too low are likely not good matches
    try:
        sold_price = float(
            item_data.get("sellingStatus", {})
            .get("currentPrice", {})
            .get("__value__", 0)
        )
        if 5 <= sold_price <= 10000:  # Reasonable price range
            score += 0.05
    except:
        pass
    max_score += 0.05

    return score / max_score if max_score > 0 else 0.0


def fetch_ebay_sold_comps_api(
    query: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
    category: Optional[str] = None,
    max_results: int = 20,
    days_lookback: int = 90,
) -> List[SoldComp]:
    """
    Fetch sold comparables from eBay using official API with ML-style matching.
    """

    # Check for API credentials (OAuth token preferred, App ID fallback)
    ebay_oauth_token = getattr(settings, "EBAY_OAUTH_TOKEN", None)
    ebay_app_id = getattr(settings, "EBAY_APP_ID", None)

    if not ebay_oauth_token and not ebay_app_id:
        print("eBay API credentials not configured")
        return []

    client = EbayAPIClient(app_id=ebay_app_id, oauth_token=ebay_oauth_token)

    # Build smart search query with priority:
    # 1. UPC/ASIN (most specific)
    # 2. Brand + Model (highly specific)
    # 3. Product title (general)
    search_queries = []

    if upc:
        search_queries.append(f"UPC {upc}")
    if asin:
        search_queries.append(f"ASIN {asin}")
    if brand and model:
        search_queries.append(f"{brand} {model}")
    if query:
        search_queries.append(query)

    all_comps = []
    search_terms = {
        "title": query,
        "brand": brand,
        "model": model,
        "category": category,
    }

    for search_query in search_queries[:2]:  # Limit to top 2 search strategies
        print(f"Searching eBay API for: {search_query}")

        try:
            response = client.search_sold_listings(
                query=search_query, max_results=max_results, days_back=days_lookback
            )

            items = (
                response.get("findCompletedItemsResponse", [{}])[0]
                .get("searchResult", [{}])[0]
                .get("item", [])
            )
            if not items:
                print(f"No eBay results for: {search_query}")
                continue

            print(f"Found {len(items)} eBay listings")

            for item in items:
                try:
                    # Extract pricing data
                    selling_status = item.get("sellingStatus", [{}])[0]
                    price_info = selling_status.get("currentPrice", [{}])[0]
                    sold_price = float(price_info.get("__value__", 0))

                    if sold_price < 1:  # Skip invalid prices
                        continue

                    # Extract item details
                    title = item.get("title", [""])[0]
                    item_id = item.get("itemId", [""])[0]
                    end_time = item.get("listingInfo", [{}])[0].get("endTime", [""])[0]

                    # Calculate similarity score using ML-style features
                    similarity = calculate_similarity_score(
                        {"title": title, "sellingStatus": selling_status}, search_terms
                    )

                    # Only include high-confidence matches
                    if similarity < 0.3:  # 30% minimum similarity threshold
                        continue

                    # Parse end time
                    sold_date = None
                    if end_time:
                        try:
                            sold_date = datetime.fromisoformat(
                                end_time.replace("Z", "+00:00")
                            )
                        except:
                            sold_date = datetime.now(timezone.utc)

                    comp = SoldComp(
                        source="ebay_api",
                        price=sold_price,
                        title=title,
                        url=f"https://www.ebay.com/itm/{item_id}",
                        sold_date=sold_date,
                        condition=condition_hint or "Unknown",
                        match_score=similarity,
                        raw_data={
                            "item_id": item_id,
                            "search_query": search_query,
                            "api_response": item,
                        },
                    )

                    all_comps.append(comp)

                except Exception as e:
                    print(f"Error processing eBay item: {e}")
                    continue

            # Rate limiting - be respectful to eBay API
            time.sleep(1.0)

        except Exception as e:
            print(f"eBay API search failed for '{search_query}': {e}")
            continue

    # Sort by match score and return best results
    all_comps.sort(key=lambda x: x.match_score or 0, reverse=True)
    return all_comps[:max_results]


# Integration function to replace the old scraper
def fetch_sold_comps(
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
    Main interface for eBay sold comparables - uses API instead of scraping.
    """
    return fetch_ebay_sold_comps_api(
        query=query,
        brand=brand,
        model=model,
        upc=upc,
        asin=asin,
        condition_hint=condition_hint,
        max_results=max_results,
        days_lookback=days_lookback,
    )
