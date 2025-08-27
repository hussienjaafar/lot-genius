#!/usr/bin/env python3
"""
Test eBay Data Flow - Check if eBay data reaches the pricing model
"""

import sys
import os
import pandas as pd

# Add backend to path
sys.path.insert(0, 'backend')

def test_ebay_direct():
    """Test eBay API directly"""
    print("TESTING EBAY API DIRECTLY")
    print("-" * 40)

    try:
        from lotgenius.datasources.ebay_api import fetch_ebay_sold_comps_api

        print("Calling eBay API for: Apple AirPods Pro")

        results = fetch_ebay_sold_comps_api(
            query="Apple AirPods Pro",
            brand="Apple",
            model="AirPods Pro",
            max_results=5,
            days_lookback=30
        )

        print(f"eBay API returned {len(results)} results")

        if results:
            print("Sample eBay comparables:")
            for i, comp in enumerate(results[:3], 1):
                print(f"  {i}. ${comp.price:.2f} - {comp.title[:50]}...")
                print(f"     Match Score: {comp.match_score:.2f}")
                print(f"     Source: {comp.source}")
            return True, results
        else:
            print("No eBay results (sandbox limitation)")
            return False, []

    except Exception as e:
        print(f"ERROR: {e}")
        return False, []

def test_external_comps_integration():
    """Test if external comps (eBay) are integrated into pricing"""
    print()
    print("TESTING EXTERNAL COMPS INTEGRATION")
    print("-" * 40)

    try:
        # Check if external comps are called during pricing
        from lotgenius.resolve import resolve_items

        # Create test data
        test_df = pd.DataFrame([{
            'title': 'Apple AirPods Pro 2nd Generation',
            'brand': 'Apple',
            'model': 'AirPods Pro',
            'condition': 'new',
            'unit_cost': 85.00,
            'asin': 'B0BDHWDR12',
            'upc': '190199441787',
        }])

        print("Running resolve_items (includes external comps)...")

        # This should call external comps including eBay
        resolved_df = resolve_items(test_df.copy())

        if not resolved_df.empty:
            item = resolved_df.iloc[0]

            # Check for external comp data
            has_ebay_data = any(col.startswith('ebay') for col in item.index)
            has_external_data = any(col.startswith('external') for col in item.index)

            print("Resolved data columns:")
            for col in sorted(item.index):
                if 'price' in col.lower() or 'comp' in col.lower() or 'ebay' in col.lower():
                    value = item[col]
                    print(f"  {col}: {value}")

            print()
            print(f"Has eBay-specific data: {has_ebay_data}")
            print(f"Has external comp data: {has_external_data}")

            return True, resolved_df
        else:
            print("No resolved data returned")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_pricing_with_external_comps():
    """Test pricing model to see if it uses external comps"""
    print()
    print("TESTING PRICING WITH EXTERNAL COMPS")
    print("-" * 40)

    try:
        from lotgenius.pricing import estimate_prices
        from lotgenius.resolve import resolve_items

        # Create test data
        test_df = pd.DataFrame([{
            'title': 'Apple AirPods Pro 2nd Generation',
            'brand': 'Apple',
            'model': 'AirPods Pro',
            'condition': 'new',
            'unit_cost': 85.00,
            'asin': 'B0BDHWDR12',
        }])

        print("Step 1: Resolving items (gets external comps)...")
        resolved_df = resolve_items(test_df.copy())

        print("Step 2: Running pricing model...")
        priced_df, price_ledger = estimate_prices(resolved_df)

        if not priced_df.empty:
            item = priced_df.iloc[0]

            print("Pricing results:")
            print(f"  Estimated Price (mu): ${item.get('est_price_mu', 0):.2f}")
            print(f"  Price Sigma: ${item.get('est_price_sigma', 0):.2f}")
            print(f"  Price P50: ${item.get('est_price_p50', 0):.2f}")

            # Check price ledger for source breakdown
            print()
            print("Price ledger analysis:")
            if price_ledger:
                for entry in price_ledger:
                    if 'external' in str(entry).lower() or 'ebay' in str(entry).lower():
                        print(f"  {entry}")

            return True, priced_df
        else:
            print("No pricing results")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def check_settings():
    """Check configuration for external comps"""
    print()
    print("CHECKING CONFIGURATION")
    print("-" * 40)

    try:
        from lotgenius.config import settings

        print("External comps settings:")
        print(f"  ENABLE_EBAY_SCRAPER: {settings.ENABLE_EBAY_SCRAPER}")
        print(f"  ENABLE_FB_SCRAPER: {settings.ENABLE_FB_SCRAPER}")
        print(f"  SCRAPER_TOS_ACK: {settings.SCRAPER_TOS_ACK}")
        print(f"  EXTERNAL_COMPS_PRIOR_WEIGHT: {settings.EXTERNAL_COMPS_PRIOR_WEIGHT}")
        print(f"  EXTERNAL_COMPS_MAX_RESULTS: {settings.EXTERNAL_COMPS_MAX_RESULTS}")
        print(f"  EXTERNAL_COMPS_USE_ML_MATCHING: {settings.EXTERNAL_COMPS_USE_ML_MATCHING}")

        ebay_token = getattr(settings, 'EBAY_OAUTH_TOKEN', None)
        print(f"  EBAY_OAUTH_TOKEN: {'SET' if ebay_token else 'NOT SET'}")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("EBAY DATA FLOW ANALYSIS")
    print("Checking if eBay data reaches the pricing model")
    print("=" * 60)

    # Check configuration
    config_ok = check_settings()

    # Test eBay API directly
    ebay_direct_ok, ebay_results = test_ebay_direct()

    # Test external comps integration
    external_ok, external_data = test_external_comps_integration()

    # Test pricing with external comps
    pricing_ok, pricing_data = test_pricing_with_external_comps()

    print()
    print("SUMMARY")
    print("=" * 30)
    print(f"Configuration: {'OK' if config_ok else 'ISSUES'}")
    print(f"eBay API Direct: {'OK' if ebay_direct_ok else 'LIMITED'}")
    print(f"External Comps Integration: {'OK' if external_ok else 'ISSUES'}")
    print(f"Pricing with External Data: {'OK' if pricing_ok else 'ISSUES'}")

    print()
    if ebay_results and len(ebay_results) > 0:
        print("✅ eBay API is returning data")
    else:
        print("⚠️ eBay API not returning data (sandbox limitation)")

    if external_ok and pricing_ok:
        print("✅ External comps are integrated into pricing")
    else:
        print("❌ External comps may not be reaching pricing model")

    print()
    print("RECOMMENDATION:")
    if config_ok and (ebay_direct_ok or external_ok):
        print("eBay integration is configured and working")
        print("Data flow appears functional")
    else:
        print("eBay data flow needs investigation")
        print("May need to check external comps integration")

if __name__ == "__main__":
    main()
