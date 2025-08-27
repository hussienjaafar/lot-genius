import pandas as pd

# Test how extracted Keepa data flows through the pipeline
from lotgenius.evidence import passes_evidence_gate

# Create a test item with our extracted Keepa data
test_item = {
    "title": "Apple AirPods Pro 2nd Generation",
    "asin": "B0BDHWDR12",
    "condition": "New",
    "category": "electronics",
    "brand": "Apple",
    # Add extracted Keepa data
    "keepa_new_price": 229.70,
    "keepa_used_price": 242.54,
    "keepa_offers_count": 4,
    "keepa_salesrank_med": 4079,
    # Add some typical enriched data
    "est_price_mu": 229.70,
    "est_price_sigma": 15.00,
    "est_price_p50": 225.00,
}

print("=== TESTING EVIDENCE GATE ===")
print(f'Test item: {test_item["title"]}')
print(f'Has ASIN: {bool(test_item.get("asin"))}')
print(f'Keepa new price: ${test_item.get("keepa_new_price", 0):.2f}')
print(f'Offers count: {test_item.get("keepa_offers_count", 0)}')

try:
    # Test evidence gate
    result = passes_evidence_gate(test_item)
    print("\nEvidence gate result:")
    print(f"  Passes: {result.passes}")
    print(f"  Reason: {result.reason}")
    if hasattr(result, "details") and result.details:
        print(f"  Details: {result.details}")

    # Test with a pandas Series as well (how it's actually called)
    print("\n=== TESTING WITH PANDAS SERIES ===")
    df = pd.DataFrame([test_item])
    series_item = df.iloc[0]
    result2 = passes_evidence_gate(series_item)
    print("Series evidence gate result:")
    print(f"  Passes: {result2.passes}")
    print(f"  Reason: {result2.reason}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
