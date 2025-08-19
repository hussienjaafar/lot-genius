import pandas as pd
from lotgenius.sell import estimate_sell_p60


def _mkdf(rank, offers, mu=50.0, sigma=10.0):
    return pd.DataFrame(
        [
            {
                "sku_local": "X",
                "keepa_sales_rank_med": rank,
                "keepa_offers_count": offers,
                "est_price_mu": mu,
                "est_price_sigma": sigma,
                "est_price_p50": mu,
            }
        ]
    )


def test_monotonic_rank_improves_p60():
    """Test that better rank (lower number) improves p60."""
    df_hi = _mkdf(rank=10_000, offers=5)
    df_lo = _mkdf(rank=200_000, offers=5)
    out_hi, _ = estimate_sell_p60(df_hi)
    out_lo, _ = estimate_sell_p60(df_lo)
    assert float(out_hi.loc[0, "sell_p60"]) > float(out_lo.loc[0, "sell_p60"])


def test_offers_saturation_lowers_p60():
    """Test that more offers (competition) lowers p60."""
    df_few = _mkdf(rank=50_000, offers=2)
    df_many = _mkdf(rank=50_000, offers=40)
    out_few, _ = estimate_sell_p60(df_few)
    out_many, _ = estimate_sell_p60(df_many)
    assert float(out_few.loc[0, "sell_p60"]) > float(out_many.loc[0, "sell_p60"])


def test_price_multiplier_affects_p60():
    """Test that higher price multiplier lowers p60."""
    df = _mkdf(rank=50_000, offers=5)
    out_lo, _ = estimate_sell_p60(df, list_price_multiplier=0.9)
    out_hi, _ = estimate_sell_p60(df, list_price_multiplier=1.2)
    assert float(out_lo.loc[0, "sell_p60"]) > float(out_hi.loc[0, "sell_p60"])


def test_evidence_structure():
    """Test that evidence records have the expected structure."""
    df = _mkdf(rank=50_000, offers=5)
    out_df, events = estimate_sell_p60(df, days=60)

    assert len(events) == 1
    event = events[0]
    assert event["source"] == "sell:estimate"
    assert event["ok"] is True
    assert "meta" in event
    meta = event["meta"]

    # Check required meta fields
    required_fields = [
        "days",
        "list_price",
        "rank",
        "offers",
        "mu",
        "sigma",
        "ptm_z",
        "daily_sales_market",
        "hazard_daily",
    ]
    for field in required_fields:
        assert field in meta, f"Missing {field} in evidence meta"


def test_columns_added():
    """Test that all expected columns are added to the output DataFrame."""
    df = _mkdf(rank=50_000, offers=5)
    out_df, _ = estimate_sell_p60(df)

    expected_cols = [
        "sell_p60",
        "sell_hazard_daily",
        "sell_ptm_z",
        "sell_rank_used",
        "sell_offers_used",
    ]
    for col in expected_cols:
        assert col in out_df.columns, f"Missing column {col}"

    # Verify data types and ranges
    assert 0.0 <= out_df.loc[0, "sell_p60"] <= 1.0
    assert out_df.loc[0, "sell_hazard_daily"] >= 0.0
    assert out_df.loc[0, "sell_rank_used"] == 50_000.0
    assert out_df.loc[0, "sell_offers_used"] == 5
