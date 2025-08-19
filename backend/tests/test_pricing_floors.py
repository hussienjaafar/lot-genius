import pandas as pd
import tempfile
from pathlib import Path
from lotgenius.pricing import estimate_prices


def _df(rows):
    return pd.DataFrame(rows)


def test_category_floor_abs_applied_when_p5_below():
    """Test that absolute category floor is applied when P5 is below the floor."""
    # Create temp category priors file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"Electronics": {"p20_floor_abs": 50.0, "p20_floor_frac_of_mu": 0.1}}')
        priors_path = Path(f.name)

    try:
        df = _df(
            [
                {
                    "sku_local": "A1",
                    "condition": "New",
                    "category": "Electronics",
                    "keepa_price_new_med": 20.0,  # μ≈20, P5≈16.4, below 50.0 floor
                    "keepa_offers_count": 5,
                }
            ]
        )

        out, ledger = estimate_prices(
            df, cv_fallback=0.2, category_priors_path=priors_path
        )

        # Check that floor was applied
        assert out.loc[0, "est_price_p5_floored"] == 50.0
        assert out.loc[0, "est_price_floor_rule"] == "category_abs"
        assert out.loc[0, "est_price_category"] == "Electronics"
        assert out.loc[0, "est_price_p5"] < 50.0  # Original P5 was below floor

    finally:
        priors_path.unlink()


def test_category_floor_frac_applied_when_p5_below():
    """Test that fractional category floor is applied when P5 is below the floor."""
    # Create temp category priors file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"Books": {"p20_floor_abs": null, "p20_floor_frac_of_mu": 0.8}}')
        priors_path = Path(f.name)

    try:
        df = _df(
            [
                {
                    "sku_local": "B1",
                    "condition": "Used-Good",
                    "category": "Books",
                    "keepa_price_used_med": 20.0,  # μ≈20, 80% floor = 16.0, P5 around 14.6
                    "keepa_offers_count": 3,
                }
            ]
        )

        out, ledger = estimate_prices(
            df, cv_fallback=0.2, category_priors_path=priors_path
        )

        # Check that fractional floor was applied
        mu = out.loc[0, "est_price_mu"]
        expected_floor = mu * 0.8
        assert abs(out.loc[0, "est_price_p5_floored"] - expected_floor) < 0.01
        assert out.loc[0, "est_price_floor_rule"] == "category_frac"
        assert out.loc[0, "est_price_category"] == "Books"

    finally:
        priors_path.unlink()


def test_salvage_floor_applied():
    """Test that salvage floor is applied when P5 is below the salvage floor."""
    df = _df(
        [
            {
                "sku_local": "C1",
                "condition": "New",
                "keepa_price_new_med": 100.0,  # μ≈100, P5 around 76.7, 85% salvage = 85.0
                "keepa_offers_count": 4,
            }
        ]
    )

    out, ledger = estimate_prices(df, cv_fallback=0.2, salvage_floor_frac=0.85)

    # Check that salvage floor was applied
    mu = out.loc[0, "est_price_mu"]
    expected_salvage = mu * 0.85
    assert abs(out.loc[0, "est_price_p5_floored"] - expected_salvage) < 0.01
    assert out.loc[0, "est_price_floor_rule"] == "salvage"
    assert (
        out.loc[0, "est_price_category"] == "default"
    )  # No category provided, fallback to "default"


def test_no_floor_applied_when_p5_above_floors():
    """Test that no floor is applied when P5 is above all floors."""
    # Create temp category priors file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"Electronics": {"p20_floor_abs": 5.0, "p20_floor_frac_of_mu": 0.1}}')
        priors_path = Path(f.name)

    try:
        df = _df(
            [
                {
                    "sku_local": "D1",
                    "condition": "New",
                    "category": "Electronics",
                    "keepa_price_new_med": 200.0,  # P5 around 32.8, above both 5.0 and 20.0 (10%)
                    "keepa_offers_count": 8,
                }
            ]
        )

        out, ledger = estimate_prices(
            df,
            cv_fallback=0.2,
            category_priors_path=priors_path,
            salvage_floor_frac=0.05,  # 5% = 10.0, still below P5
        )

        # Check that no floor was applied
        original_p5 = out.loc[0, "est_price_p5"]
        floored_p5 = out.loc[0, "est_price_p5_floored"]
        assert abs(original_p5 - floored_p5) < 0.01  # Should be same
        assert pd.isna(out.loc[0, "est_price_floor_rule"])
        assert out.loc[0, "est_price_category"] == "Electronics"

    finally:
        priors_path.unlink()


def test_highest_floor_wins():
    """Test that the highest floor is applied when multiple floors are available."""
    # Create temp category priors file with both abs and frac floors
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(
            '{"Electronics": {"p20_floor_abs": 90.0, "p20_floor_frac_of_mu": 0.85}}'
        )
        priors_path = Path(f.name)

    try:
        df = _df(
            [
                {
                    "sku_local": "E1",
                    "condition": "New",
                    "category": "Electronics",
                    "keepa_price_new_med": 100.0,  # μ≈100, P5≈79.2, abs_floor=90, frac_floor=85, salvage=80
                    "keepa_offers_count": 5,
                }
            ]
        )

        out, ledger = estimate_prices(
            df,
            cv_fallback=0.2,
            category_priors_path=priors_path,
            salvage_floor_frac=0.80,  # 80% = 80.0
        )

        # Check that highest floor (absolute 90.0) was applied
        assert out.loc[0, "est_price_p5_floored"] == 90.0
        assert out.loc[0, "est_price_floor_rule"] == "category_abs"
        assert out.loc[0, "est_price_category"] == "Electronics"

    finally:
        priors_path.unlink()


def test_category_floor_uses_category_hint():
    """Test that floors trigger with category_hint column."""
    from pathlib import Path

    priors_path = Path("backend/tests/fixtures/category_priors.json")
    df = _df(
        [
            {
                "sku_local": "E3",
                "condition": "New",
                "category_hint": "electronics",
                "keepa_price_new_med": 30.0,
                "keepa_offers_count": 4,
            }
        ]
    )

    out, _ = estimate_prices(
        df, category_priors_path=priors_path, salvage_floor_frac=0.0
    )
    assert float(out.loc[0, "est_price_p5_floored"]) >= 25.0
    assert "category" in (out.loc[0, "est_price_floor_rule"] or "")


def test_category_fallback_to_default():
    """Test category fallback tracking when requested category not in priors."""
    from pathlib import Path

    priors_path = Path("backend/tests/fixtures/category_priors.json")
    df = _df(
        [
            {
                "sku_local": "F1",
                "condition": "New",
                "category": "UnknownCategory",  # Not in priors file
                "keepa_price_new_med": 50.0,
                "keepa_offers_count": 3,
            }
        ]
    )

    out, ledger = estimate_prices(
        df, category_priors_path=priors_path, salvage_floor_frac=None
    )

    # Check that category fell back to "default"
    assert out.loc[0, "est_price_category"] == "default"

    # Check evidence meta has fallback tracking
    evidence = ledger[0]
    meta = evidence.meta
    assert meta["category_requested"] == "UnknownCategory"
    assert meta["category_used"] == "default"
    assert meta["category_fallback"] is True

    # Check unified naming in evidence meta
    assert "est_price_p5" in meta
    assert "est_price_p5_floored" in meta
    # Backward-compat keys should still exist
    assert "p5" in meta
    assert "p5_floored" in meta


def test_used_category_written_and_meta_present(tmp_path):
    """Test used category fallback is written correctly and evidence meta always includes keys."""
    import json

    priors = {"default": {"p20_floor_abs": None, "p20_floor_frac_of_mu": 0.0}}
    p = tmp_path / "priors.json"
    p.write_text(json.dumps(priors), encoding="utf-8")
    df = pd.DataFrame(
        [
            {
                "sku_local": "W1",
                "condition": "New",
                "category_hint": "widgets_not_in_priors",
                "keepa_price_new_med": 40.0,
                "keepa_offers_count": 4,
            }
        ]
    )
    out, ledger = estimate_prices(
        df, category_priors_path=str(p), salvage_floor_frac=0.0
    )
    assert out.loc[0, "est_price_category"] == "default"
    ev = next(e for e in ledger if e.source == "price:estimate")
    assert ev.meta["category_requested"] == "widgets_not_in_priors"
    assert ev.meta["category_used"] == "default"
    assert ev.meta["category_fallback"] is True
    assert "est_price_p5" in ev.meta and "est_price_p5_floored" in ev.meta
