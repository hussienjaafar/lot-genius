from pathlib import Path

from lotgenius.validation import validate_manifest_csv


def test_utf8_bom_in_content(tmp_path: Path):
    p = tmp_path / "bom_content.csv"
    # Write a minimal CSV with a UTF-8 BOM at file start
    text = "SKU,Item Name,Qty\nA-1,Widget,1\n"
    p.write_text(text, encoding="utf-8-sig")
    rep = validate_manifest_csv(p, fuzzy_threshold=85)
    assert rep.passed, f"Should pass despite BOM: {rep.notes}"
    assert (
        rep.header_coverage >= 2 / 3
    )  # SKU->sku_local, Item Name->title, Qty->quantity
