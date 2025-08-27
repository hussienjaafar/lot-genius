"""Test payout lag functionality in ROI calculations."""

import pandas as pd
import pytest
from lotgenius.roi import simulate_lot_outcomes


@pytest.fixture
def sample_items_df():
    """Create a sample items DataFrame for testing."""
    data = {
        "est_price_mu": [100.0, 80.0, 120.0],
        "est_price_sigma": [10.0, 8.0, 12.0],
        "sell_p60": [0.8, 0.6, 0.7],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_items_with_hazard_df():
    """Create a sample items DataFrame with explicit sell_hazard_daily."""
    data = {
        "est_price_mu": [100.0, 80.0],
        "est_price_sigma": [10.0, 8.0],
        "sell_p60": [0.8, 0.6],
        "sell_hazard_daily": [0.025, 0.015],  # Explicit daily hazard rates
    }
    return pd.DataFrame(data)


def test_payout_lag_reduces_cash_60d(sample_items_df, monkeypatch):
    """Test that increasing payout lag reduces expected_cash_60d."""
    bid = 150.0

    # Test Case A: No payout lag
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "0")

    # Force reload of settings
    import lotgenius.config
    import lotgenius.roi
    from lotgenius.config import Settings

    lotgenius.config.settings = Settings()
    # Also need to reload the roi module to pick up new settings
    import importlib

    importlib.reload(lotgenius.roi)

    result_a = simulate_lot_outcomes(sample_items_df, bid, sims=1000, seed=42)

    # Test Case B: 30-day payout lag
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "30")

    # Force reload of settings again
    lotgenius.config.settings = Settings()
    importlib.reload(lotgenius.roi)

    result_b = simulate_lot_outcomes(sample_items_df, bid, sims=1000, seed=42)

    # Assertions
    assert result_a["payout_lag_days"] == 0
    assert result_b["payout_lag_days"] == 30

    # Expected cash in Case B should be less than Case A
    expected_cash_a = float((result_a["cash_60d"]).mean())
    expected_cash_b = float((result_b["cash_60d"]).mean())

    assert (
        expected_cash_b < expected_cash_a
    ), f"Expected cash with lag ({expected_cash_b}) should be less than without lag ({expected_cash_a})"

    # Revenue should be unchanged (lag doesn't affect total revenue, just timing)
    revenue_a = float((result_a["revenue"]).mean())
    revenue_b = float((result_b["revenue"]).mean())

    # Revenue should be approximately equal (may have small differences due to randomness)
    assert (
        abs(revenue_a - revenue_b) < 0.01 * revenue_a
    ), f"Revenue should be approximately equal: {revenue_a} vs {revenue_b}"


def test_payout_lag_extreme_case(sample_items_df, monkeypatch):
    """Test extreme case where payout lag >= horizon."""
    bid = 150.0

    # Set payout lag >= horizon (60 days)
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "70")

    # Force reload of settings
    import lotgenius.config
    import lotgenius.roi
    from lotgenius.config import Settings

    lotgenius.config.settings = Settings()
    import importlib

    importlib.reload(lotgenius.roi)

    result = simulate_lot_outcomes(sample_items_df, bid, sims=1000, seed=42)

    # When lag >= horizon, no cash should be received within horizon
    expected_cash = float((result["cash_60d"]).mean())
    assert (
        expected_cash == 0.0
    ), f"Expected cash should be 0 when lag >= horizon, got {expected_cash}"

    # But revenue should still be positive (includes salvage)
    revenue = float((result["revenue"]).mean())
    assert revenue > 0, f"Revenue should still be positive, got {revenue}"

    assert result["payout_lag_days"] == 70


def test_payout_lag_with_explicit_hazard(sample_items_with_hazard_df, monkeypatch):
    """Test payout lag calculation with explicit sell_hazard_daily values."""
    bid = 120.0

    # Test with moderate payout lag
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "20")

    # Force reload of settings
    import lotgenius.config
    import lotgenius.roi
    from lotgenius.config import Settings

    lotgenius.config.settings = Settings()
    import importlib

    importlib.reload(lotgenius.roi)

    result = simulate_lot_outcomes(sample_items_with_hazard_df, bid, sims=1000, seed=42)

    # Check that result includes expected metadata
    assert result["payout_lag_days"] == 20
    assert "cash_60d" in result
    assert "revenue" in result

    # Cash should be reduced but not zero
    expected_cash = float((result["cash_60d"]).mean())
    revenue = float((result["revenue"]).mean())

    assert (
        0 < expected_cash < revenue
    ), f"Expected cash ({expected_cash}) should be positive but less than revenue ({revenue})"


def test_payout_lag_zero_sell_probability(monkeypatch):
    """Test payout lag handling with items that have zero sell probability."""
    data = {
        "est_price_mu": [100.0],
        "est_price_sigma": [10.0],
        "sell_p60": [0.0],  # Zero sell probability
    }
    df = pd.DataFrame(data)
    bid = 50.0

    # Test with payout lag
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "20")

    # Force reload of settings
    import lotgenius.config
    import lotgenius.roi
    from lotgenius.config import Settings

    lotgenius.config.settings = Settings()
    import importlib

    importlib.reload(lotgenius.roi)

    result = simulate_lot_outcomes(df, bid, sims=1000, seed=42)

    # With zero sell probability, cash should be zero regardless of lag
    expected_cash = float((result["cash_60d"]).mean())
    assert (
        expected_cash == 0.0
    ), f"Expected cash should be 0 with zero sell probability, got {expected_cash}"


def test_payout_lag_percentiles_consistency(sample_items_df, monkeypatch):
    """Test that cash percentiles are consistent with payout lag."""
    bid = 150.0

    # Test with moderate payout lag
    monkeypatch.setenv("PAYOUT_LAG_DAYS", "15")

    # Force reload of settings
    import lotgenius.config
    import lotgenius.roi
    from lotgenius.config import Settings

    lotgenius.config.settings = Settings()
    import importlib

    importlib.reload(lotgenius.roi)

    result = simulate_lot_outcomes(sample_items_df, bid, sims=2000, seed=42)

    # Check that percentiles are ordered correctly
    cash_p5 = result["cash_60d_p5"]
    cash_p50 = result["cash_60d_p50"]
    cash_p95 = result["cash_60d_p95"]

    assert (
        cash_p5 <= cash_p50 <= cash_p95
    ), f"Cash percentiles should be ordered: P5({cash_p5}) <= P50({cash_p50}) <= P95({cash_p95})"

    # Check that they reflect the lag-adjusted cash_60d array
    import numpy as np

    actual_p5 = float(np.quantile(result["cash_60d"], 0.05))
    actual_p50 = float(np.quantile(result["cash_60d"], 0.50))
    actual_p95 = float(np.quantile(result["cash_60d"], 0.95))

    assert abs(cash_p5 - actual_p5) < 0.01, f"P5 mismatch: {cash_p5} vs {actual_p5}"
    assert (
        abs(cash_p50 - actual_p50) < 0.01
    ), f"P50 mismatch: {cash_p50} vs {actual_p50}"
    assert (
        abs(cash_p95 - actual_p95) < 0.01
    ), f"P95 mismatch: {cash_p95} vs {actual_p95}"


def test_payout_lag_default_setting():
    """Test that payout lag uses default setting of 14 days."""
    from lotgenius.config import settings

    # Reset to clean state
    settings_fresh = settings.__class__()
    assert settings_fresh.PAYOUT_LAG_DAYS == 14

    # Test with minimal DataFrame
    data = {
        "est_price_mu": [50.0],
        "est_price_sigma": [5.0],
        "sell_p60": [0.5],
    }
    df = pd.DataFrame(data)

    result = simulate_lot_outcomes(df, 25.0, sims=100, seed=42)

    # Should include payout_lag_days in result
    assert "payout_lag_days" in result
    # Note: We can't assert the exact value here because the environment may have been modified
    # by other tests, but we can check it's a reasonable integer
    assert isinstance(result["payout_lag_days"], int)
    assert result["payout_lag_days"] >= 0
