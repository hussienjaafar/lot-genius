"""
Facebook Marketplace integration using Facebook Graph API and alternative methods.
Since Facebook doesn't provide direct marketplace API access, we use creative approaches.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import settings
from .base import SoldComp


def calculate_product_match_score(
    listing: Dict[str, Any], target: Dict[str, Any]
) -> float:
    """
    Advanced ML-style product matching using multiple signals.
    """
    score = 0.0
    max_score = 0.0

    # Text similarity using simple but effective methods
    listing_text = f"{listing.get('name', '')} {listing.get('description', '')}".lower()
    target_title = target.get("title", "").lower()
    target_brand = target.get("brand", "").lower()
    target_model = target.get("model", "").lower()

    # Brand matching (high weight - 35%)
    if target_brand and target_brand in listing_text:
        score += 0.35
    max_score += 0.35

    # Model matching (high weight - 30%)
    if target_model and target_model in listing_text:
        score += 0.30
    max_score += 0.30

    # Title word overlap (moderate weight - 25%)
    if target_title:
        target_words = set(target_title.split())
        listing_words = set(listing_text.split())
        if target_words and listing_words:
            overlap_ratio = len(target_words & listing_words) / len(target_words)
            score += overlap_ratio * 0.25
    max_score += 0.25

    # Price reasonableness (10%)
    try:
        price = (
            float(listing.get("price", {}).get("amount", 0)) / 100
        )  # Facebook stores in cents
        if 1 <= price <= 50000:  # Reasonable price range
            score += 0.10
    except:
        pass
    max_score += 0.10

    return score / max_score if max_score > 0 else 0.0


class FacebookMarketplaceAPI:
    """
    Facebook Marketplace data fetching using alternative methods.
    Since Facebook restricts marketplace API access, we use creative approaches.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.graph_url = "https://graph.facebook.com/v18.0"

    def search_marketplace_alternative(
        self, query: str, location: str = "United States", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Alternative marketplace search using public data sources.
        """
        results = []

        # Method 1: Use Facebook's public search (limited but sometimes works)
        try:
            results.extend(self._public_search(query, max_results // 2))
        except Exception as e:
            print(f"Public Facebook search failed: {e}")

        # Method 2: Use third-party marketplace aggregators
        try:
            results.extend(self._aggregator_search(query, max_results // 2))
        except Exception as e:
            print(f"Aggregator search failed: {e}")

        return results[:max_results]

    def _public_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using Facebook's limited public endpoints."""
        # This would require careful implementation to avoid ToS violations
        # For now, return empty to avoid legal issues
        print("Facebook public search not implemented (ToS compliance)")
        return []

    def _aggregator_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using third-party marketplace aggregators that index Facebook."""
        # Services like SearchTempest, Marketplace Pulse, etc.
        # This would require partnerships or API access with aggregators
        print("Third-party aggregator search not implemented")
        return []


def fetch_facebook_comps_enhanced(
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
    Enhanced Facebook Marketplace comparable fetching with ML matching.
    """

    # Check if Facebook integration is enabled and properly configured
    fb_token = getattr(settings, "FACEBOOK_ACCESS_TOKEN", None)
    if not fb_token or not settings.SCRAPER_TOS_ACK:
        print("Facebook integration not configured or not enabled")
        return []

    client = FacebookMarketplaceAPI(fb_token)

    # Build prioritized search terms
    search_terms = []
    if upc:
        search_terms.append(f"{upc}")
    if brand and model:
        search_terms.append(f"{brand} {model}")
    if query:
        search_terms.append(query)

    all_comps = []
    target_data = {"title": query, "brand": brand, "model": model}

    for search_term in search_terms[:2]:  # Limit searches to avoid rate limits
        print(f"Searching Facebook alternatives for: {search_term}")

        try:
            listings = client.search_marketplace_alternative(
                query=search_term, location=location, max_results=max_results
            )

            for listing in listings:
                try:
                    # Extract price
                    price_data = listing.get("price", {})
                    price_amount = price_data.get("amount", 0)
                    if isinstance(price_amount, str):
                        price_amount = float(price_amount)

                    price = (
                        price_amount / 100 if price_amount > 100 else price_amount
                    )  # Handle cents vs dollars

                    if price < 1:
                        continue

                    # Calculate match score
                    match_score = calculate_product_match_score(listing, target_data)

                    if (
                        match_score < 0.4
                    ):  # 40% minimum threshold for Facebook (higher than eBay)
                        continue

                    # Create comparable
                    comp = SoldComp(
                        source="facebook_api",
                        price=price,
                        title=listing.get("name", "Facebook Marketplace Listing"),
                        url=f"https://facebook.com/marketplace/item/{listing.get('id', '')}",
                        sold_date=datetime.now(
                            timezone.utc
                        ),  # Facebook doesn't provide sold date
                        condition=condition_hint or "Unknown",
                        match_score=match_score,
                        raw_data={
                            "listing_id": listing.get("id"),
                            "search_term": search_term,
                            "location": location,
                            "facebook_data": listing,
                        },
                    )

                    all_comps.append(comp)

                except Exception as e:
                    print(f"Error processing Facebook listing: {e}")
                    continue

            # Rate limiting
            time.sleep(2.0)

        except Exception as e:
            print(f"Facebook search failed for '{search_term}': {e}")
            continue

    # Sort by match score
    all_comps.sort(key=lambda x: x.match_score or 0, reverse=True)
    return all_comps[:max_results]


# Integration function
def fetch_sold_comps_from_facebook(
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
    Main interface for Facebook Marketplace comparables.
    """
    return fetch_facebook_comps_enhanced(
        query=query,
        brand=brand,
        model=model,
        upc=upc,
        asin=asin,
        condition_hint=condition_hint,
        max_results=max_results,
        location=location,
    )
