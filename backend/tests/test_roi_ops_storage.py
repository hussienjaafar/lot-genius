import numpy as np
import pandas as pd
from lotgenius.roi import simulate_lot_outcomes


def _mkdf_single(mu=100.0, sigma=0.0, p=1.0, mins_per_unit=None, quantity=1):
    d = {
        "sku_local": ["X1"],
        "est_price_mu": [mu],
        "est_price_sigma": [sigma],
        "sell_p60": [p],
        "quantity": [quantity],
    }
    if mins_per_unit is not None:
        d["mins_per_unit"] = [mins_per_unit]
    return pd.DataFrame(d)


def test_ops_cost_decreases_cash_and_revenue():
    df = _mkdf_single(mu=100.0, sigma=0.0, p=1.0, mins_per_unit=5.0, quantity=1)
    base = simulate_lot_outcomes(
        df,
        bid=0.0,
        sims=10,
        seed=1,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        ops_cost_per_min=0.0,
    )
    with_ops = simulate_lot_outcomes(
        df,
        bid=0.0,
        sims=10,
        seed=1,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        ops_cost_per_min=1.0,
    )
    # Ops minutes = 5 => cost 5; subtracts from both cash and revenue
    assert np.isclose(with_ops["cash_60d_p50"] + 5.0, base["cash_60d_p50"], atol=1e-6)
    assert np.isclose(with_ops["cash_60d_p5"] + 5.0, base["cash_60d_p5"], atol=1e-6)


def test_storage_cost_decreases_cash_expected():
    # p60 = 0 -> expect holding days = horizon (60)
    df = _mkdf_single(mu=100.0, sigma=0.0, p=0.0, quantity=2)
    base = simulate_lot_outcomes(
        df,
        bid=0.0,
        sims=5,
        seed=2,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        storage_cost_per_unit_per_day=0.0,
    )
    with_storage = simulate_lot_outcomes(
        df,
        bid=0.0,
        sims=5,
        seed=2,
        marketplace_fee_pct=0.0,
        payment_fee_pct=0.0,
        per_order_fee_fixed=0.0,
        return_rate=0.0,
        salvage_frac=0.0,
        storage_cost_per_unit_per_day=1.0,
    )
    # quantity=2, horizon=60 -> total storage cost 120
    assert np.isclose(
        base["cash_60d_p50"], with_storage["cash_60d_p50"] + 120.0, atol=1e-6
    )
