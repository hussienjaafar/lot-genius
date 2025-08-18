from lotgenius.schema import ConditionEnum, Item, item_jsonschema


def test_item_schema_roundtrip():
    it = Item(
        sku_local="A-1",
        title="Gadget",
        brand="Acme",
        model="G-100",
        upc_ean_asin="012345678905",
        condition=ConditionEnum.LikeNew,
        quantity=2,
        est_cost_per_unit=12.34,
        notes="note",
        category_hint="Kitchen",
        msrp=49.99,
        color_size_variant="Red/L",
        lot_id="LOT-1",
    )
    js = item_jsonschema()
    assert isinstance(js, dict)
    assert "properties" in js
    assert js["properties"]["title"]["type"] == "string"
    assert it.quantity == 2


def test_quantity_positive():
    try:
        Item(title="x", quantity=0)
        assert False, "should have raised"
    except Exception:
        pass
