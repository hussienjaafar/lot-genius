#!/usr/bin/env python3
"""
Direct Pipeline Test - Test individual components
"""

import sys
import os
import pandas as pd
import tempfile

# Add backend to path
sys.path.insert(0, 'backend')

def test_keepa_integration():
    """Test Keepa data extraction"""
    print("TESTING KEEPA INTEGRATION")
    print("-" * 40)

    try:
        from lotgenius.keepa_extract import fetch_keepa_data_batch

        # Test with AirPods Pro ASIN
        asins = ["B0BDHWDR12"]  # AirPods Pro 2nd Gen
        print(f"Testing ASIN: {asins[0]} (AirPods Pro)")

        results = fetch_keepa_data_batch(asins, max_workers=1)

        if results:
            result = results[0]
            print(f"SUCCESS: Got Keepa data")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  New Price: ${result.get('price_new_median', 0):.2f}")
            print(f"  Amazon URL: {result.get('amazon_url', 'N/A')}")
            return True, result
        else:
            print("No Keepa results returned")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        return False, None

def test_ebay_integration():
    """Test eBay API integration"""
    print()
    print("TESTING EBAY INTEGRATION")
    print("-" * 40)

    try:
        from lotgenius.datasources.ebay_api import fetch_ebay_sold_comps_api

        print("Testing: Apple AirPods Pro")

        results = fetch_ebay_sold_comps_api(
            query="Apple AirPods Pro",
            brand="Apple",
            model="AirPods Pro",
            max_results=3,
            days_lookback=30
        )

        if results:
            print(f"SUCCESS: Found {len(results)} eBay comparables")
            for i, comp in enumerate(results[:2], 1):
                print(f"  {i}. ${comp.price:.2f} - {comp.title[:50]}...")
                print(f"     Match: {comp.match_score:.2f} | Source: {comp.source}")
            return True, results
        else:
            print("No eBay results (expected in sandbox)")
            return True, []  # This is OK for sandbox

    except Exception as e:
        print(f"ERROR: {e}")
        return False, None

def test_pricing_models():
    """Test pricing model directly"""
    print()
    print("TESTING PRICING MODELS")
    print("-" * 40)

    try:
        from lotgenius.pricing import estimate_prices

        # Create test data with Keepa price
        test_df = pd.DataFrame([{
            'title': 'Apple AirPods Pro 2nd Generation',
            'brand': 'Apple',
            'model': 'AirPods Pro',
            'condition': 'new',
            'unit_cost': 85.00,
            'keepa_new_price': 249.00,
            'keepa_new_mu': 249.00,
            'keepa_price_new_med': 249.00,
        }])

        print("Input data:")
        print(f"  Title: {test_df.iloc[0]['title']}")
        print(f"  Cost: ${test_df.iloc[0]['unit_cost']:.2f}")
        print(f"  Keepa Price: ${test_df.iloc[0]['keepa_new_price']:.2f}")

        result_df, price_ledger = estimate_prices(test_df)

        if not result_df.empty:
            item = result_df.iloc[0]
            est_price = item.get('est_price_mu', 0)
            print(f"SUCCESS: Pricing model completed")
            print(f"  Estimated Price: ${est_price:.2f}")

            if est_price > 0:
                roi_potential = est_price / test_df.iloc[0]['unit_cost']
                print(f"  ROI Potential: {roi_potential:.2f}x")
                return True, result_df
            else:
                print("  WARNING: No price estimate")
                return False, None
        else:
            print("ERROR: No pricing results")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_sell_probability():
    """Test sell probability model"""
    print()
    print("TESTING SELL PROBABILITY MODEL")
    print("-" * 40)

    try:
        from lotgenius.sell import estimate_sell_p60

        # Create test data with estimated price
        test_df = pd.DataFrame([{
            'title': 'Apple AirPods Pro 2nd Generation',
            'brand': 'Apple',
            'model': 'AirPods Pro',
            'condition': 'new',
            'unit_cost': 85.00,
            'est_price_mu': 240.00,
            'est_price_sigma': 20.00,
        }])

        print("Input data:")
        print(f"  Title: {test_df.iloc[0]['title']}")
        print(f"  Est Price: ${test_df.iloc[0]['est_price_mu']:.2f}")

        result_df, sell_ledger = estimate_sell_p60(test_df, days=60)

        if not result_df.empty:
            item = result_df.iloc[0]
            sell_p60 = item.get('sell_p60', 0)
            print(f"SUCCESS: Sell probability model completed")
            print(f"  60-day Sell Probability: {sell_p60:.1%}")

            if sell_p60 > 0:
                expected_revenue = test_df.iloc[0]['est_price_mu'] * sell_p60
                roi = expected_revenue / test_df.iloc[0]['unit_cost']
                print(f"  Expected Revenue: ${expected_revenue:.2f}")
                print(f"  ROI: {roi:.2f}x")
                return True, result_df
            else:
                print("  WARNING: No sell probability")
                return False, None
        else:
            print("ERROR: No sell probability results")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        return False, None

def test_bid_optimization():
    """Test bid optimization"""
    print()
    print("TESTING BID OPTIMIZATION")
    print("-" * 40)

    try:
        from lotgenius.roi import optimize_bid

        # Create test data for portfolio
        test_df = pd.DataFrame([
            {
                'title': 'Apple AirPods Pro 2nd Generation',
                'unit_cost': 85.00,
                'quantity': 12,
                'est_price_mu': 240.00,
                'est_price_sigma': 20.00,
                'sell_p60': 0.85,
            },
            {
                'title': 'Samsung Galaxy S23 Ultra',
                'unit_cost': 650.00,
                'quantity': 8,
                'est_price_mu': 950.00,
                'est_price_sigma': 50.00,
                'sell_p60': 0.75,
            }
        ])

        total_cost = (test_df['unit_cost'] * test_df['quantity']).sum()
        print(f"Portfolio cost: ${total_cost:,.2f}")

        # Test bid optimization
        bid_result = optimize_bid(test_df)

        if bid_result:
            print(f"SUCCESS: Bid optimization completed")
            print(f"  Recommended Bid: ${bid_result['optimal_bid']:,.2f}")
            print(f"  Expected ROI: {bid_result['expected_roi']:.2f}x")
            print(f"  Success Probability: {bid_result['success_probability']:.1%}")
            return True, bid_result
        else:
            print("ERROR: No bid recommendation")
            return False, None

    except Exception as e:
        print(f"ERROR: {e}")
        return False, None

def evaluate_full_pipeline():
    """Evaluate the complete pipeline capability"""
    print()
    print("FULL PIPELINE EVALUATION")
    print("=" * 50)

    # Test individual stages
    keepa_ok, keepa_data = test_keepa_integration()
    ebay_ok, ebay_data = test_ebay_integration()
    pricing_ok, pricing_data = test_pricing_models()
    sell_ok, sell_data = test_sell_probability()
    bid_ok, bid_data = test_bid_optimization()

    print()
    print("COMPONENT STATUS:")
    print(f"  Keepa Integration: {'PASS' if keepa_ok else 'FAIL'}")
    print(f"  eBay Integration: {'PASS' if ebay_ok else 'FAIL'}")
    print(f"  Pricing Models: {'PASS' if pricing_ok else 'FAIL'}")
    print(f"  Sell Probability: {'PASS' if sell_ok else 'FAIL'}")
    print(f"  Bid Optimization: {'PASS' if bid_ok else 'FAIL'}")

    # Overall assessment
    critical_components = [keepa_ok, pricing_ok, sell_ok, bid_ok]
    all_critical_working = all(critical_components)

    print()
    print("OVERALL ASSESSMENT:")
    if all_critical_working:
        print("  STATUS: READY FOR TESTING")
        print("  CONFIDENCE: MODERATE to HIGH")
        print("  RECOMMENDATION: Start with small test purchases")
    elif sum(critical_components) >= 3:
        print("  STATUS: PARTIALLY READY")
        print("  CONFIDENCE: LOW to MODERATE")
        print("  RECOMMENDATION: Fix missing components first")
    else:
        print("  STATUS: NOT READY")
        print("  CONFIDENCE: LOW")
        print("  RECOMMENDATION: Major fixes needed")

    print()
    print("NEXT STEPS:")
    print("1. Test with small liquidation purchases ($100-500)")
    print("2. Compare app predictions vs actual outcomes")
    print("3. Adjust risk parameters based on results")
    print("4. Gradually increase purchase amounts")
    print("5. Always validate high-value decisions manually")

def main():
    print("LIQUIDATION APP - COMPONENT TESTING")
    print("Testing individual pipeline stages with real data")
    print("=" * 60)

    evaluate_full_pipeline()

    print()
    print("COMPONENT TESTING COMPLETE!")
    print("Review results above for app readiness assessment.")

if __name__ == "__main__":
    main()
