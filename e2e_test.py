import sys
import os
sys.path.insert(0, 'backend')
from lotgenius.api.service import run_optimize
import json

# Test with realistic liquidation manifest and business parameters
opt_config = {
    'lo': 0,
    'hi': 5000,
    'roi_target': 1.5,
    'risk_threshold': 0.75,
    'min_cash_60d': 1000,
    'sims': 500,
    'marketplace_fee_pct': 0.15,
    'payment_fee_pct': 0.03,
    'return_rate': 0.10
}

# Write config to temp file
with open('e2e_test_config.json', 'w') as f:
    json.dump(opt_config, f)

print('=== E2E TEST: REALISTIC LIQUIDATION LOT ===')
print('Running full pipeline with 20-item manifest...')
print('Config: 50% ROI target, 75% success rate, $1000 min cash flow')
print()

try:
    result, out_path = run_optimize(
        'realistic_liquidation_manifest.csv',
        'e2e_test_config.json',
        'e2e_full_result.json'
    )

    print('✅ PIPELINE COMPLETED SUCCESSFULLY')
    print()
    print('=== BUSINESS DECISION ANALYSIS ===')
    print(f'Items processed: {result.get("items", 0)}')
    print(f'Core items (high confidence): {result.get("core_items_count", 0)}')
    print(f'Review items (lower confidence): {result.get("upside_items_count", 0)}')
    print()
    print('=== BID RECOMMENDATION ===')
    print(f'Recommended bid: ${result.get("bid", 0):.2f}')
    print(f'Expected ROI: {result.get("roi_p50", 0):.2f}x ({(result.get("roi_p50", 1) - 1) * 100:.1f}% profit)')
    print(f'Conservative ROI (5th percentile): {result.get("roi_p5", 0):.2f}x')
    print(f'Optimistic ROI (95th percentile): {result.get("roi_p95", 0):.2f}x')
    print()
    print('=== RISK ASSESSMENT ===')
    print(f'Success probability: {result.get("prob_roi_ge_target", 0) * 100:.1f}%')
    print(f'Meets all constraints: {"✅ YES" if result.get("meets_constraints", False) else "❌ NO"}')
    print(f'Risk-adjusted ROI (CVaR): {result.get("roi_cvar", 0):.2f}x')
    print()
    print('=== CASH FLOW PROJECTION ===')
    print(f'Expected 60-day cash flow: ${result.get("expected_cash_60d", 0):.2f}')
    print(f'Conservative cash (5th percentile): ${result.get("cash_60d_p5", 0):.2f}')
    print(f'Median cash (50th percentile): ${result.get("cash_60d_p50", 0):.2f}')
    print()
    if result.get('review', False):
        print('⚠️  RECOMMENDATION: Manual review suggested due to high upside item value')
    else:
        print('✅ RECOMMENDATION: Safe to proceed with automated decision')

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
