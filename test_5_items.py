import sys
import os
sys.path.insert(0, 'backend')
from lotgenius.api.service import run_optimize
import json

# Test with 5-item subset and realistic liquidation business parameters
opt_config = {
    'lo': 0,
    'hi': 10000,
    'roi_target': 1.5,
    'risk_threshold': 0.75,
    'min_cash_60d': 500,
    'sims': 500,
    'marketplace_fee_pct': 0.15,
    'payment_fee_pct': 0.03,
    'return_rate': 0.10,
    'mins_per_unit': 8,
    'capacity_mins_per_day': 480
}

# Write config to temp file
with open('test_5_items_config.json', 'w') as f:
    json.dump(opt_config, f)

print('=== E2E TEST: 5-ITEM LIQUIDATION LOT ===')
print('Items: AirPods Pro, Samsung TV, Nike Shoes, Instant Pot, Dyson Vacuum')
print('Business model: 50% ROI target, 75% success rate, $500 min cash flow')
print()

try:
    result, out_path = run_optimize(
        'test_5_items.csv',
        'test_5_items_config.json',
        'test_5_items_result.json'
    )

    print('✅ PIPELINE COMPLETED SUCCESSFULLY')
    print()
    print('=== BUSINESS DECISION ANALYSIS ===')
    print(f'Items processed: {result.get("items", 0)}')
    print(f'Core items (high confidence): {result.get("core_items_count", 0)}')
    print(f'Review items (lower confidence): {result.get("upside_items_count", 0)}')
    print()
    print('=== BID RECOMMENDATION ===')
    print(f'Recommended maximum bid: ${result.get("bid", 0):.2f}')
    print(f'Expected ROI: {result.get("roi_p50", 0):.2f}x ({(result.get("roi_p50", 1) - 1) * 100:.1f}% profit)')
    print(f'Conservative ROI (worst case): {result.get("roi_p5", 0):.2f}x ({(result.get("roi_p5", 1) - 1) * 100:.1f}% profit)')
    print(f'Optimistic ROI (best case): {result.get("roi_p95", 0):.2f}x ({(result.get("roi_p95", 1) - 1) * 100:.1f}% profit)')
    print()
    print('=== RISK ASSESSMENT ===')
    print(f'Success probability: {result.get("prob_roi_ge_target", 0) * 100:.1f}%')
    print(f'Meets all business constraints: {"✅ YES" if result.get("meets_constraints", False) else "❌ NO"}')
    print(f'Risk-adjusted ROI (CVaR): {result.get("roi_cvar", 0):.2f}x')
    print()
    print('=== OPERATIONAL FEASIBILITY ===')
    throughput = result.get('throughput', {})
    print(f'Processing time required: {throughput.get("total_minutes_required", 0):.0f} minutes')
    print(f'Daily capacity available: {throughput.get("available_minutes", 0):.0f} minutes')
    print(f'Throughput constraint: {"✅ OK" if throughput.get("throughput_ok", False) else "❌ EXCEEDED"}')
    print()

    # Business decision logic
    roi_ok = result.get("roi_p5", 0) >= opt_config['roi_target']
    risk_ok = result.get("prob_roi_ge_target", 0) >= opt_config['risk_threshold']
    constraint_ok = result.get("meets_constraints", False)

    print('=== FINAL BUSINESS RECOMMENDATION ===')
    if roi_ok and risk_ok and constraint_ok:
        print('🟢 PROCEED WITH LOT PURCHASE')
        print(f'   Max bid: ${result.get("bid", 0):.2f}')
        print(f'   Expected profit: {(result.get("roi_p50", 1) - 1) * result.get("bid", 0):.2f}')
        print('   Risk level: ACCEPTABLE')
    elif result.get('review', False):
        print('🟡 PROCEED WITH MANUAL REVIEW')
        print('   High-value items need individual assessment')
    else:
        print('🔴 DO NOT PURCHASE LOT')
        reasons = []
        if not roi_ok: reasons.append('ROI too low')
        if not risk_ok: reasons.append('Success probability too low')
        if not constraint_ok: reasons.append('Constraints not met')
        print(f'   Reasons: {", ".join(reasons)}')

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
