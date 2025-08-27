#!/usr/bin/env python3

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_smart_scrapers():
    """Test smart scrapers with fallback to mock data."""
    from lotgenius.datasources.smart_scrapers import (
        smart_ebay_scraper,
        smart_facebook_scraper,
        smart_google_scraper,
        get_all_comparable_data
    )

    print("=== TESTING SMART SCRAPERS (WITH MOCK FALLBACK) ===\n")

    test_query = "Apple iPhone 14"
    test_brand = "Apple"
    test_model = "iPhone 14"

    print(f"Testing with query: {test_query}\n")

    # Test individual scrapers
    print("1. Testing Smart eBay Scraper:")
    ebay_results = smart_ebay_scraper(test_query, test_brand, test_model, max_results=5)
    print(f"   Results: {len(ebay_results)}")
    if ebay_results:
        for i, result in enumerate(ebay_results[:2]):
            print(f"   {i+1}. {result.title[:50]} - ${result.price:.2f} [{result.source}]")

    print("\n2. Testing Smart Facebook Scraper:")
    facebook_results = smart_facebook_scraper(test_query, test_brand, test_model, max_results=5)
    print(f"   Results: {len(facebook_results)}")
    if facebook_results:
        for i, result in enumerate(facebook_results[:2]):
            location = result.meta.get('location', 'Unknown') if result.meta else 'Unknown'
            print(f"   {i+1}. {result.title[:50]} - ${result.price:.2f} [{result.source}] ({location})")

    print("\n3. Testing Smart Google Scraper:")
    google_results = smart_google_scraper(test_query, test_brand, test_model, max_results=5)
    print(f"   Results: {len(google_results)}")
    if google_results:
        for i, result in enumerate(google_results[:2]):
            print(f"   {i+1}. {result.title[:50]} - ${result.price:.2f} [{result.source}]")

    print("\n4. Testing Comprehensive Data Collection:")
    all_results = get_all_comparable_data(test_query, test_brand, test_model, max_results_per_source=3)

    # Analyze results
    sources = {}
    total_value = 0
    for result in all_results:
        sources[result.source] = sources.get(result.source, 0) + 1
        total_value += result.price

    print(f"\n=== COMPREHENSIVE RESULTS ===")
    print(f"Total results: {len(all_results)}")
    print(f"Source breakdown: {dict(sources)}")
    if all_results:
        avg_price = total_value / len(all_results)
        min_price = min(r.price for r in all_results)
        max_price = max(r.price for r in all_results)
        print(f"Price analysis: Avg=${avg_price:.2f}, Min=${min_price:.2f}, Max=${max_price:.2f}")

    return len(all_results) > 0

def test_mock_data_variety():
    """Test mock data with different product types."""
    from lotgenius.datasources.smart_scrapers import get_all_comparable_data

    print("\n=== TESTING MOCK DATA VARIETY ===\n")

    test_items = [
        ("Nintendo Switch", "Nintendo", "Switch"),
        ("MacBook Pro", "Apple", "MacBook Pro"),
        ("PlayStation 5", "Sony", "PlayStation 5"),
        ("AirPods Pro", "Apple", "AirPods Pro"),
    ]

    for query, brand, model in test_items:
        print(f"Testing: {query}")
        results = get_all_comparable_data(query, brand, model, max_results_per_source=2)
        if results:
            prices = [r.price for r in results]
            print(f"  {len(results)} results, price range: ${min(prices):.2f} - ${max(prices):.2f}")
        else:
            print(f"  No results for {query}")
        print()

if __name__ == "__main__":
    success = test_smart_scrapers()
    test_mock_data_variety()

    print("\n=== FINAL STATUS ===")
    if success:
        print("✓ SUCCESS: Smart scrapers are working with mock fallback!")
        print("✓ The pricing engine now has reliable data sources.")
        print("\nNOTE: Using mock data for development. For production:")
        print("- Consider eBay API (requires approval)")
        print("- Facebook API doesn't allow marketplace scraping")
        print("- Google Custom Search API (limited free tier)")
    else:
        print("✗ FAILED: Smart scrapers are not working")
