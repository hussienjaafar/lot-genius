import pandas as pd
from lotgenius.roi import simulate_lot_outcomes


def _mkdf_single(mu=100.0, sigma=0.0, p=1.0):
    return pd.DataFrame(
        {
            "sku_local": ["X1"],
            "est_price_mu": [mu],
            "est_price_sigma": [sigma],
            "sell_p60": [p],
        }
    )


def test_missing_rate_all_kills_revenue():
    df = _mkdf_single(mu=100.0, sigma=0.0, p=1.0)
    mc = simulate_lot_outcomes(
        df,
        bid=100.0,
        sims=200,
        seed=123,
        # zero fees/returns to isolate effect
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        # manifest risk
        missing_rate=1.0,
        missing_recovery_frac=0.0,
    )
    assert mc["roi_p50"] == 0.0
    assert mc["cash_60d_p50"] == 0.0


def test_defect_recovery_scales_revenue():
    df = _mkdf_single(mu=100.0, sigma=0.0, p=1.0)
    mc = simulate_lot_outcomes(
        df,
        bid=100.0,
        sims=50,
        seed=42,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        defect_rate=1.0,
        defect_recovery_frac=0.5,
    )
    # With 100% defect and 50% recovery, median ROI ~= 0.5
    assert 0.49 <= mc["roi_p50"] <= 0.51


def test_mismatch_discount_reduces_revenue():
    df = _mkdf_single(mu=100.0, sigma=0.0, p=1.0)
    mc = simulate_lot_outcomes(
        df,
        bid=100.0,
        sims=50,
        seed=7,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        grade_mismatch_rate=1.0,
        mismatch_discount_frac=0.2,
    )
    # 20% discount -> ROI around 0.8
    assert 0.79 <= mc["roi_p50"] <= 0.81
