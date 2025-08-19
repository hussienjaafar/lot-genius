import pandas as pd
from lotgenius.roi import feasible, optimize_bid, simulate_lot_outcomes


def _mkdf(n=10, mu=60.0, sigma=12.0, p=0.6):
    return pd.DataFrame(
        {
            "sku_local": [f"S{i}" for i in range(n)],
            "est_price_mu": mu,
            "est_price_sigma": sigma,
            "sell_p60": p,
        }
    )


def test_simulate_shapes_and_quantiles():
    """Test basic simulation shapes and quantile ordering."""
    df = _mkdf(n=5)
    mc = simulate_lot_outcomes(df, bid=100.0, sims=500, seed=42)
    assert mc["items"] == 5 and mc["sims"] == 500
    assert 0.0 <= mc["roi_p5"] <= mc["roi_p95"]


def test_feasible_probability_gate():
    """Test that feasible() correctly gates on probability threshold."""
    df = _mkdf(n=20, mu=80.0, sigma=10.0, p=0.9)
    ok_low, _ = feasible(
        df, bid=200.0, roi_target=1.25, risk_threshold=0.80, sims=500, seed=1
    )
    ok_high, _ = feasible(
        df, bid=5000.0, roi_target=1.25, risk_threshold=0.80, sims=500, seed=1
    )
    assert ok_low is True and ok_high is False


def test_optimize_bid_bisection_monotone():
    """Test that bisection produces monotonic behavior with stricter targets."""
    df = _mkdf(n=10, mu=60.0, sigma=12.0, p=0.6)
    res = optimize_bid(
        df,
        lo=0.0,
        hi=2000.0,
        sims=500,
        seed=7,
        roi_target=1.25,
        risk_threshold=0.8,
        tol=5.0,
    )
    assert 0.0 <= res["bid"] <= 2000.0
    # sanity: raising target lowers recommended bid
    res2 = optimize_bid(
        df,
        lo=0.0,
        hi=2000.0,
        sims=500,
        seed=7,
        roi_target=1.40,
        risk_threshold=0.8,
        tol=5.0,
    )
    assert res2["bid"] <= res["bid"]


def test_empty_dataframe_handling():
    """Test that empty dataframes are handled gracefully."""
    df = pd.DataFrame()
    mc = simulate_lot_outcomes(df, bid=100.0, sims=100, seed=42)
    assert mc["items"] == 0
    assert mc["roi_p5"] == 0.0 and mc["roi_p50"] == 0.0 and mc["roi_p95"] == 0.0


def test_missing_columns_handling():
    """Test handling of missing columns with fallbacks."""
    df = pd.DataFrame({"sku_local": ["A"], "est_price_mu": [50.0]})
    # Should infer sigma and sell_p60
    mc = simulate_lot_outcomes(df, bid=10.0, sims=100, seed=42)
    assert mc["items"] == 1  # Should not drop the item
    assert mc["roi_p50"] >= 0.0  # Should produce reasonable ROI


def test_lot_fixed_cost_reduces_bid():
    """Test that lot fixed cost reduces the recommended bid."""
    df = _mkdf(n=8)
    res1 = optimize_bid(
        df, lo=0, hi=2000, sims=300, seed=1, roi_target=1.25, risk_threshold=0.8
    )
    res2 = optimize_bid(
        df,
        lo=0,
        hi=2000,
        sims=300,
        seed=1,
        roi_target=1.25,
        risk_threshold=0.8,
        lot_fixed_cost=200.0,
    )
    assert res2["bid"] <= res1["bid"]


def test_cash_p5_constraint_bites():
    """Test that cash P5 constraint is included in result."""
    df = _mkdf(n=5, p=0.4)
    res = optimize_bid(
        df,
        lo=0,
        hi=2000,
        sims=300,
        seed=2,
        roi_target=1.1,
        risk_threshold=0.7,
        min_cash_60d_p5=50.0,
    )
    assert "cash_60d_p5" in res
