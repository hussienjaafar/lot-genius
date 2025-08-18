from lotgenius.headers import learn_alias, map_headers


def test_map_headers_synonyms():
    headers = [
        "SKU",
        "Item Name",
        "Brand",
        "Model Number",
        "UPC",
        "Cond.",
        "Qty",
        "List Price",
        "Notes",
        "Department",
        "Color/Size",
        "Lot",
    ]
    mapping, unmapped = map_headers(headers, threshold=85)
    assert mapping["SKU"] == "sku_local"
    assert mapping["Item Name"] == "title"
    assert mapping["Model Number"] == "model"
    assert mapping["UPC"] == "upc_ean_asin"
    assert mapping["Cond."] == "condition"
    assert mapping["Qty"] == "quantity"
    assert mapping["List Price"] == "msrp"
    assert mapping["Department"] == "category_hint"
    assert mapping["Color/Size"] == "color_size_variant"
    assert mapping["Lot"] == "lot_id"
    assert unmapped == []  # in this fixture we expect perfect coverage


def test_learn_alias_persists(tmp_path, monkeypatch):
    # Redirect alias store to a temp file
    from lotgenius import headers as h

    h.ALIAS_STORE = tmp_path / "aliases.json"

    # Unknown header becomes learned alias
    mapping, unmapped = map_headers(["WeirdHdr"], threshold=95)
    assert "WeirdHdr" in unmapped

    learn_alias("WeirdHdr", "notes")
    mapping2, unmapped2 = map_headers(["WeirdHdr"], threshold=95)
    assert mapping2["WeirdHdr"] == "notes"
    assert unmapped2 == []
