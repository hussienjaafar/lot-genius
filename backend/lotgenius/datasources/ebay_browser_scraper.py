"""
eBay scraper using playwright for better anti-blocking capabilities.
This is more reliable than direct HTTP requests for scraping eBay.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from ..config import settings
from .base import SoldComp


def _sleep_jitter(base=1.2, spread=0.8):
    """Sleep with random jitter to appear more human-like."""
    time.sleep(base + random.random() * spread)


def _build_ebay_search_url(query: str) -> str:
    """Build eBay sold listings search URL."""
    from urllib.parse import quote

    return f"https://www.ebay.com/sch/i.html?_nkw={quote(query)}&LH_Sold=1&LH_Complete=1&_sop=13"


def _parse_price_text(text: str) -> Optional[float]:
    """Extract price from text string."""
    import re

    # Remove currency symbols and extra characters
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None

    # Handle comma thousands separators
    if "," in cleaned and "." in cleaned:
        # Format like "1,234.56"
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned and cleaned.count(",") == 1 and len(cleaned.split(",")[1]) <= 2:
        # Format like "1234,56" (European style)
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_sold_comps_browser(
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
    Fetch sold comparables from eBay using playwright browser automation.
    More reliable than direct HTTP requests.
    """
    if not HAS_PLAYWRIGHT:
        print("Playwright not available - falling back to empty results")
        return []

    if not settings.SCRAPER_TOS_ACK or not settings.ENABLE_EBAY_SCRAPER:
        return []

    # Build search query with priority: UPC > ASIN > Brand+Model > Query
    if upc:
        search_query = f'"{upc}"'
    elif asin:
        search_query = f'"{asin}"'
    elif brand and model:
        search_query = f'"{brand}" "{model}"'
    else:
        search_query = query

    print(f"Searching eBay for: {search_query}")

    try:
        with sync_playwright() as p:
            # Launch browser with realistic settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            # Create context with realistic viewport and user agent
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )

            page = context.new_page()

            # Navigate to eBay search
            search_url = _build_ebay_search_url(search_query)
            print(f"Navigating to: {search_url}")

            page.goto(search_url, wait_until="networkidle", timeout=30000)
            _sleep_jitter(2.0, 1.0)

            # Wait for search results to load
            try:
                page.wait_for_selector(".s-item", timeout=10000)
            except:
                print("No search results found or page didn't load properly")
                browser.close()
                return []

            # Extract sold listings
            items = page.query_selector_all(".s-item")
            results = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)

            print(f"Found {len(items)} potential items")

            for i, item in enumerate(
                items[: max_results * 2]
            ):  # Get extra for filtering
                try:
                    # Get title
                    title_elem = item.query_selector(".s-item__title")
                    if not title_elem:
                        continue
                    title = title_elem.inner_text().strip()

                    # Skip sponsored/ad items
                    if "SPONSORED" in title.upper() or title.startswith("Shop on eBay"):
                        continue

                    # Get price
                    price_elem = item.query_selector(".s-item__price")
                    if not price_elem:
                        continue
                    price_text = price_elem.inner_text().strip()
                    price = _parse_price_text(price_text)
                    if not price or price <= 0:
                        continue

                    # Get URL
                    link_elem = item.query_selector("a.s-item__link")
                    url = link_elem.get_attribute("href") if link_elem else None

                    # Get sold date if available
                    date_elem = item.query_selector(".s-item__ended-date")
                    sold_at = None
                    if date_elem:
                        date_text = date_elem.inner_text().strip()
                        # Try to parse date (eBay uses various formats)
                        for fmt in ["%b %d, %Y", "%b %d %Y", "%m/%d/%Y"]:
                            try:
                                # Extract just the date part
                                date_part = date_text.split()[
                                    -3:
                                ]  # Last 3 words usually contain date
                                date_str = " ".join(date_part)
                                sold_at = datetime.strptime(date_str, fmt).replace(
                                    tzinfo=timezone.utc
                                )
                                break
                            except:
                                continue

                    # Apply recency filter
                    if sold_at and sold_at < cutoff_date:
                        continue

                    # Create SoldComp object
                    comp = SoldComp(
                        source="ebay_browser",
                        title=title[:300],
                        price=price,
                        condition=condition_hint or "Unknown",
                        sold_at=sold_at,
                        url=url,
                        id=None,
                        match_score=0.8,  # Default score, can be refined later
                        meta={
                            "raw_price": price_text,
                            "query": search_query,
                            "scrape_method": "playwright",
                        },
                    )

                    results.append(comp)

                    if len(results) >= max_results:
                        break

                except Exception as e:
                    print(f"Error processing item {i}: {e}")
                    continue

            browser.close()
            print(f"Successfully scraped {len(results)} items from eBay")
            return results

    except Exception as e:
        print(f"eBay browser scraping failed: {e}")
        return []


# For backward compatibility, alias the browser version as main function
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
    """Main interface - uses browser scraping for better reliability."""
    return fetch_sold_comps_browser(
        query, brand, model, upc, asin, condition_hint, max_results, days_lookback
    )
