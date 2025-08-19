from pathlib import Path

from lotgenius.parse import parse_and_clean


def test_parse_and_clean_basic(tmp_path: Path):
    p = Path("backend/tests/fixtures/manifest_multiqty.csv")
    res = parse_and_clean(p, fuzzy_threshold=85, explode=False)

    # Mapping: these headers should be covered
    assert "title" in res.df_clean.columns
    assert "brand" in res.df_clean.columns
    assert "model" in res.df_clean.columns
    assert "upc_ean_asin" in res.df_clean.columns
    assert "quantity" in res.df_clean.columns
    assert res.unmapped_headers == []  # given fixture uses synonyms

    # Cleaning: numeric coercion & ID normalization
    assert res.df_clean["quantity"].dtype.kind in ("i", "I")  # integer
    assert res.df_clean["msrp"].dtype.kind in ("f", "F")  # float
    # upc stripped to alnum
    assert all(x is None or x.isalnum() for x in res.df_clean["upc_ean_asin"].tolist())


def test_condition_normalization_and_explode(tmp_path: Path):
    p = Path("backend/tests/fixtures/manifest_multiqty.csv")
    res = parse_and_clean(p, fuzzy_threshold=85, explode=True)
    exploded = res.df_exploded
    assert exploded is not None

    # Rows explode: 3 + 5 + 2 = 10
    assert exploded.shape[0] == 10

    # quantity set to 1 for each exploded row
    assert exploded["quantity"].eq(1).all()

    # condition normalized to enum string values or None
    assert set(exploded["condition"].dropna().unique()).issubset(
        {"New", "LikeNew", "UsedGood", "UsedFair", "Salvage"}
    )

    # unit_index present and 1-based within parent
    assert exploded["unit_index"].min() == 1
    assert exploded["unit_index"].max() >= 2

    # back-pointer preserved (lot_id exists)
    assert "lot_id" in exploded.columns
