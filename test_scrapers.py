#!/usr/bin/env python3

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_google_scraper():
    """Test the Google search scraper."""
    try:
        from lotgenius.datasources.google_search import fetch_sold_comps_from_google

        print("Testing Google search scraper...")
        results = fetch_sold_comps_from_google(
            query='Nintendo Switch',
            brand='Nintendo',
            model='Switch',
            condition_hint='used',
            max_results=5
        )

        print(f'Google scraper returned {len(results)} results')
        if results:
            for i, result in enumerate(results):
                print(f'{i+1}. {result.title[:60]}')
                print(f'   Price: ${result.price:.2f} | Source: {result.source}')
                print()
            return True
        else:
            print('No results returned from Google scraper')
            return False

    except Exception as e:
        print(f'ERROR: Google scraper failed: {e}')
        return False

def test_facebook_scraper():
    """Test the Facebook marketplace scraper."""
    try:
        from lotgenius.datasources.facebook_scraper import fetch_sold_comps_from_facebook

        print("\nTesting Facebook marketplace scraper...")
        results = fetch_sold_comps_from_facebook(
            query='Nintendo Switch',
            brand='Nintendo',
            model='Switch',
            condition_hint='used',
            max_results=3
        )

        print(f'Facebook scraper returned {len(results)} results')
        if results:
            for i, result in enumerate(results):
                print(f'{i+1}. {result.title[:60]}')
                print(f'   Price: ${result.price:.2f} | Source: {result.source}')
                if result.meta and result.meta.get('location'):
                    print(f'   Location: {result.meta["location"]}')
                print()
            return True
        else:
            print('No results returned from Facebook scraper')
            return False

    except Exception as e:
        print(f'ERROR: Facebook scraper failed: {e}')
        return False

def test_original_ebay_scraper():
    """Test the original eBay scraper with improvements."""
    try:
        from lotgenius.datasources.ebay_scraper import fetch_sold_comps

        print("\nTesting original eBay scraper (with improvements)...")
        results = fetch_sold_comps(
            query='Nintendo Switch',
            brand='Nintendo',
            model='Switch',
            condition_hint='used',
            max_results=3
        )

        print(f'Original eBay scraper returned {len(results)} results')
        if results:
            for i, result in enumerate(results):
                print(f'{i+1}. {result.title[:60]}')
                print(f'   Price: ${result.price:.2f} | Source: {result.source}')
                if result.sold_at:
                    print(f'   Sold: {result.sold_at.strftime("%Y-%m-%d")}')
                print()
            return True
        else:
            print('No results returned from original eBay scraper')
            return False

    except Exception as e:
        print(f'ERROR: Original eBay scraper failed: {e}')
        return False

def test_scraper_config():
    """Test scraper configuration."""
    try:
        from lotgenius.config import settings

        print("\nTesting scraper configuration...")
        print(f"SCRAPER_TOS_ACK: {settings.SCRAPER_TOS_ACK}")
        print(f"ENABLE_EBAY_SCRAPER: {settings.ENABLE_EBAY_SCRAPER}")
        print(f"ENABLE_FB_SCRAPER: {settings.ENABLE_FB_SCRAPER}")
        print(f"ENABLE_GOOGLE_SEARCH_ENRICHMENT: {settings.ENABLE_GOOGLE_SEARCH_ENRICHMENT}")
        return True

    except Exception as e:
        print(f'ERROR: Config test failed: {e}')
        return False

if __name__ == "__main__":
    print("=== COMPREHENSIVE SCRAPER TESTING ===\n")

    # Test configuration first
    config_ok = test_scraper_config()

    # Test all scrapers
    google_success = test_google_scraper()
    facebook_success = test_facebook_scraper()
    ebay_success = test_original_ebay_scraper()

    print("\n=== RESULTS SUMMARY ===")
    print(f"Configuration: {'OK' if config_ok else 'FAILED'}")
    print(f"Google Scraper: {'WORKING' if google_success else 'FAILED'}")
    print(f"Facebook Scraper: {'WORKING' if facebook_success else 'FAILED'}")
    print(f"eBay Scraper: {'WORKING' if ebay_success else 'FAILED'}")

    working_count = sum([google_success, facebook_success, ebay_success])
    print(f"\nScraper Status: {working_count}/3 scrapers working")

    if working_count >= 1:
        print("SUCCESS: At least one scraper is functional!")
    else:
        print("WARNING: No scrapers are working - pricing data will be limited")
