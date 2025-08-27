"""Test sell-through estimation with both rank column spellings."""

import pandas as pd
from lotgenius.sell import estimate_sell_p60


def test_sell_with_keepa_salesrank_med_no_underscore():
    """Test that sell_p60 works when only keepa_salesrank_med (no underscore) exists."""
    # Create a single-row DataFrame with keepa_salesrank_med (no underscore)
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-SKU-001",
                "keepa_salesrank_med": 50_000,  # without underscore (from resolve.py)
                "keepa_offers_count": 5,
                "est_price_mu": 50.0,
                "est_price_sigma": 10.0,
                "est_price_p50": 50.0,
            }
        ]
    )

    # Run sell-through estimation
    result_df, events = estimate_sell_p60(df, days=60)

    # Verify that sell_p60 was computed and is reasonable
    assert "sell_p60" in result_df.columns
    sell_p60_value = result_df["sell_p60"].iloc[0]
    assert sell_p60_value > 0, "sell_p60 should be greater than 0"
    assert sell_p60_value <= 1, "sell_p60 should be less than or equal to 1"

    # Verify that the rank was properly detected and used
    assert "sell_rank_used" in result_df.columns
    rank_used = result_df["sell_rank_used"].iloc[0]
    assert rank_used == 50_000.0, f"Expected rank 50000, got {rank_used}"

    # Verify that offers were properly detected
    assert "sell_offers_used" in result_df.columns
    offers_used = result_df["sell_offers_used"].iloc[0]
    assert offers_used == 5, f"Expected offers 5, got {offers_used}"

    # Check that event was recorded with the rank
    assert len(events) == 1
    assert events[0]["meta"]["rank"] == 50_000.0


def test_sell_with_keepa_sales_rank_med_with_underscore():
    """Test that sell_p60 still works with keepa_sales_rank_med (with underscore)."""
    # Create a single-row DataFrame with keepa_sales_rank_med (with underscore)
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-SKU-002",
                "keepa_sales_rank_med": 75_000,  # with underscore (original)
                "keepa_offers_count": 10,
                "est_price_mu": 100.0,
                "est_price_sigma": 20.0,
                "est_price_p50": 100.0,
            }
        ]
    )

    # Run sell-through estimation
    result_df, events = estimate_sell_p60(df, days=60)

    # Verify that sell_p60 was computed and is reasonable
    assert "sell_p60" in result_df.columns
    sell_p60_value = result_df["sell_p60"].iloc[0]
    assert sell_p60_value > 0, "sell_p60 should be greater than 0"
    assert sell_p60_value <= 1, "sell_p60 should be less than or equal to 1"

    # Verify that the rank was properly detected and used
    assert "sell_rank_used" in result_df.columns
    rank_used = result_df["sell_rank_used"].iloc[0]
    assert rank_used == 75_000.0, f"Expected rank 75000, got {rank_used}"

    # Verify that offers were properly detected
    assert "sell_offers_used" in result_df.columns
    offers_used = result_df["sell_offers_used"].iloc[0]
    assert offers_used == 10, f"Expected offers 10, got {offers_used}"


def test_sell_prefers_underscore_version_when_both_exist():
    """Test that keepa_sales_rank_med (with underscore) takes precedence when both exist."""
    # Create a DataFrame with both columns
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-SKU-003",
                "keepa_sales_rank_med": 25_000,  # with underscore (should be preferred)
                "keepa_salesrank_med": 100_000,  # without underscore (should be ignored)
                "keepa_offers_count": 3,
                "est_price_mu": 75.0,
                "est_price_sigma": 15.0,
                "est_price_p50": 75.0,
            }
        ]
    )

    # Run sell-through estimation
    result_df, events = estimate_sell_p60(df, days=60)

    # Verify that the rank with underscore was used (first in priority list)
    assert "sell_rank_used" in result_df.columns
    rank_used = result_df["sell_rank_used"].iloc[0]
    assert (
        rank_used == 25_000.0
    ), f"Expected rank 25000 (with underscore), got {rank_used}"


def test_sell_fallback_when_no_rank_columns():
    """Test that sell_p60 falls back to baseline when no rank columns exist."""
    # Create a DataFrame without any rank columns
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-SKU-004",
                "keepa_offers_count": 8,
                "est_price_mu": 30.0,
                "est_price_sigma": 5.0,
                "est_price_p50": 30.0,
            }
        ]
    )

    # Run sell-through estimation with a baseline
    result_df, events = estimate_sell_p60(df, days=60, baseline_daily_sales=0.01)

    # Verify that sell_p60 was computed using baseline
    assert "sell_p60" in result_df.columns
    sell_p60_value = result_df["sell_p60"].iloc[0]
    assert sell_p60_value > 0, "sell_p60 should be greater than 0 with baseline"

    # Verify that no rank was used
    assert "sell_rank_used" in result_df.columns
    rank_used = result_df["sell_rank_used"].iloc[0]
    assert pd.isna(rank_used), f"Expected no rank (NaN), got {rank_used}"

    # Check event shows no rank but used baseline
    assert len(events) == 1
    assert events[0]["meta"]["rank"] is None
    assert events[0]["meta"]["baseline_daily_sales"] == 0.01


def test_sell_multiple_rows_mixed_column_names():
    """Test sell_p60 with multiple rows having different rank column names."""
    # Create a DataFrame with mixed column presence
    df = pd.DataFrame(
        [
            {
                "sku_local": "SKU-A",
                "keepa_sales_rank_med": 10_000,  # with underscore
                "keepa_offers_count": 2,
                "est_price_mu": 25.0,
                "est_price_sigma": 5.0,
                "est_price_p50": 25.0,
            },
            {
                "sku_local": "SKU-B",
                "keepa_salesrank_med": 20_000,  # without underscore
                "keepa_offers_count": 4,
                "est_price_mu": 50.0,
                "est_price_sigma": 10.0,
                "est_price_p50": 50.0,
            },
            {
                "sku_local": "SKU-C",
                # No rank column at all
                "keepa_offers_count": 6,
                "est_price_mu": 75.0,
                "est_price_sigma": 15.0,
                "est_price_p50": 75.0,
            },
        ]
    )

    # Run sell-through estimation
    result_df, events = estimate_sell_p60(df, days=60, baseline_daily_sales=0.005)

    # Verify all rows got sell_p60 estimates
    assert len(result_df) == 3
    assert all(result_df["sell_p60"] > 0)
    assert all(result_df["sell_p60"] <= 1)

    # Verify ranks were properly detected
    assert result_df["sell_rank_used"].iloc[0] == 10_000.0  # from keepa_sales_rank_med
    assert result_df["sell_rank_used"].iloc[1] == 20_000.0  # from keepa_salesrank_med
    assert pd.isna(result_df["sell_rank_used"].iloc[2])  # no rank column

    # Verify events match
    assert len(events) == 3
    assert events[0]["meta"]["rank"] == 10_000.0
    assert events[1]["meta"]["rank"] == 20_000.0
    assert events[2]["meta"]["rank"] is None
