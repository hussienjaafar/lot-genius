import pandas as pd
from lotgenius.pricing import estimate_prices


def _df(rows):
    return pd.DataFrame(rows)


def test_pricing_prefers_used_when_not_new():
    df = _df(
        [
            {
                "sku_local": "A",
                "condition": "Used-Good",
                "keepa_price_used_med": 120.0,
                "keepa_price_new_med": 200.0,
                "keepa_offers_count": 10,
            },
            {
                "sku_local": "B",
                "condition": "New",
                "keepa_price_used_med": 100.0,
                "keepa_price_new_med": 180.0,
                "keepa_offers_count": 5,
            },
        ]
    )
    out, ledger = estimate_prices(
        df,
        cv_fallback=0.2,
        priors={"keepa": 0.5, "ebay": 0.35, "other": 0.15},
        use_used_for_nonnew=True,
    )
    assert out.loc[0, "est_price_p50"] < out.loc[1, "est_price_p50"]  # Used < New
    assert any(e.source == "price:estimate" and e.ok for e in ledger)


def test_pricing_sigma_and_percentiles_monotonic():
    df = _df(
        [
            {
                "sku_local": "X",
                "condition": "New",
                "keepa_price_new_med": 150.0,
                "keepa_offers_count": 4,
            }
        ]
    )
    out, _ = estimate_prices(
        df,
        cv_fallback=0.25,
        priors={"keepa": 0.5, "ebay": 0.35, "other": 0.15},
        use_used_for_nonnew=True,
    )
    mu = float(out.loc[0, "est_price_mu"])
    p5, p50, p95 = (
        float(out.loc[0, "est_price_p5"]),
        float(out.loc[0, "est_price_p50"]),
        float(out.loc[0, "est_price_p95"]),
    )
    assert mu == p50
    assert p5 < p50 < p95
    assert p5 >= 0.0


def test_missing_all_sources_yields_nan():
    df = _df([{"sku_local": "Z", "condition": "Used-Good"}])
    out, ledger = estimate_prices(df)
    assert pd.isna(out.loc[0, "est_price_mu"])
    assert any((e.source == "price:estimate" and not e.ok) for e in ledger)
