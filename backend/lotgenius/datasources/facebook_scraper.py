"""
Facebook Marketplace scraper for finding sold/listed items.
"""

from __future__ import annotations

import random
import re
import time
from typing import List, Optional

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from ..config import settings
from .base import SoldComp


def _sleep_jitter(base=1.5, spread=1.0):
    """Sleep with random jitter to appear more human-like."""
    time.sleep(base + random.random() * spread)


def _parse_price_from_facebook(text: str) -> Optional[float]:
    """Extract price from Facebook Marketplace text."""
    # Facebook typically shows prices as $123 or $1,234
    price_patterns = [
        r"\$[\d,]+\.?\d*",
        r"[\d,]+\.?\d*\s*dollars?",
        r"USD\s*[\d,]+\.?\d*",
    ]

    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Take the first reasonable match
            for match in matches:
                cleaned = re.sub(r"[^\d.]", "", match)
                if cleaned:
                    try:
                        price = float(cleaned)
                        if 1 <= price <= 100000:  # Reasonable price range
                            return price
                    except ValueError:
                        continue
    return None


def _build_facebook_search_url(query: str, location: str = "United States") -> str:
    """Build Facebook Marketplace search URL."""
    from urllib.parse import quote

    # Facebook Marketplace search URL format
    base_url = "https://www.facebook.com/marketplace"
    search_path = f"/search?query={quote(query)}"
    return f"{base_url}{search_path}"


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
    Fetch comparable listings from Facebook Marketplace.
    Note: Facebook doesn't show "sold" items, but current listings can indicate market prices.
    """
    if not HAS_PLAYWRIGHT:
        print("Playwright not available for Facebook scraping")
        return []

    # Check if scraping is enabled
    scraper_enabled = getattr(settings, "ENABLE_FB_SCRAPER", False)
    if not settings.SCRAPER_TOS_ACK or not scraper_enabled:
        return []

    # Build search query with priority
    if upc:
        search_query = f"{upc}"
    elif asin:
        search_query = f"{asin}"
    elif brand and model:
        search_query = f"{brand} {model}"
    else:
        search_query = query

    if condition_hint:
        search_query += f" {condition_hint}"

    print(f"Searching Facebook Marketplace for: {search_query}")

    try:
        with sync_playwright() as p:
            # Launch browser with stealth settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )

            page = context.new_page()

            # Navigate to Facebook Marketplace
            search_url = _build_facebook_search_url(search_query, location)
            print(f"Navigating to: {search_url}")

            page.goto(search_url, wait_until="networkidle", timeout=30000)
            _sleep_jitter(2.0, 1.0)

            # Handle potential login prompts or popups
            try:
                # Look for "Not Now" or "Close" buttons for login prompts
                not_now_btn = page.query_selector(
                    'button[data-testid="cookie-policy-manage-dialog-accept-button"]'
                )
                if not_now_btn:
                    not_now_btn.click()
                    _sleep_jitter(1.0, 0.5)

                # Close any other overlays
                close_btn = page.query_selector('[aria-label="Close"]')
                if close_btn:
                    close_btn.click()
                    _sleep_jitter(1.0, 0.5)

            except:
                pass  # Ignore overlay handling errors

            # Wait for marketplace listings to load
            try:
                page.wait_for_selector(
                    '[data-testid="marketplace-product-item"]', timeout=10000
                )
            except:
                print("No marketplace items found or page didn't load properly")
                browser.close()
                return []

            # Extract listings
            listings = page.query_selector_all(
                '[data-testid="marketplace-product-item"]'
            )
            results = []

            print(f"Found {len(listings)} potential listings")

            for i, listing in enumerate(listings[:max_results]):
                try:
                    # Get title/description
                    title_elem = listing.query_selector(
                        "[data-marketplace-listing-title]"
                    )
                    if not title_elem:
                        title_elem = listing.query_selector('span[dir="auto"]')

                    title = (
                        title_elem.inner_text().strip()
                        if title_elem
                        else f"Facebook listing {i+1}"
                    )

                    # Get price
                    price_elem = listing.query_selector(
                        '[data-testid="marketplace-product-item-price"]'
                    )
                    if not price_elem:
                        price_elem = listing.query_selector('span[dir="auto"]')

                    if price_elem:
                        price_text = price_elem.inner_text().strip()
                        price = _parse_price_from_facebook(price_text)
                        if not price:
                            continue
                    else:
                        continue

                    # Get URL
                    link_elem = listing.query_selector("a")
                    url = None
                    if link_elem:
                        href = link_elem.get_attribute("href")
                        if href:
                            url = (
                                f"https://www.facebook.com{href}"
                                if href.startswith("/")
                                else href
                            )

                    # Get location info if available
                    location_elem = listing.query_selector(
                        '[data-testid="marketplace-product-item-location"]'
                    )
                    location_text = (
                        location_elem.inner_text().strip()
                        if location_elem
                        else "Unknown"
                    )

                    # Create SoldComp object
                    comp = SoldComp(
                        source="facebook_marketplace",
                        title=title[:300],
                        price=price,
                        condition=condition_hint or "Unknown",
                        sold_at=None,  # Facebook shows current listings, not sold items
                        url=url,
                        id=None,
                        match_score=0.6,  # Medium trust score
                        meta={
                            "raw_price": price_text,
                            "location": location_text,
                            "query": search_query,
                            "scrape_method": "playwright_facebook",
                        },
                    )

                    results.append(comp)

                except Exception as e:
                    print(f"Error processing Facebook listing {i}: {e}")
                    continue

            browser.close()
            print(
                f"Successfully scraped {len(results)} items from Facebook Marketplace"
            )
            return results

    except Exception as e:
        print(f"Facebook Marketplace scraping failed: {e}")
        return []


# Alias for consistency with other scrapers
fetch_sold_comps = fetch_sold_comps_from_facebook
