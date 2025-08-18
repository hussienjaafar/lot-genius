from lotgenius.headers import suggest_candidates


def test_suggest_candidates_points_to_canonical():
    out = suggest_candidates("UPC Code", top_k=5)
    # At least one suggestion should map to the canonical UPC field
    assert any(item.get("canonical") == "upc_ean_asin" for item in out)
    assert all("score" in item for item in out)


def test_suggest_candidates_structure():
    out = suggest_candidates("WeirdHeader", top_k=3)
    assert len(out) == 3
    for item in out:
        assert "candidate" in item
        assert "canonical" in item  # can be None
        assert "score" in item
        assert isinstance(item["score"], int)


def test_suggest_candidates_different_top_k():
    out1 = suggest_candidates("Brand Name", top_k=1)
    out5 = suggest_candidates("Brand Name", top_k=5)
    assert len(out1) == 1
    assert len(out5) == 5
    # First item should be the same
    assert out1[0]["candidate"] == out5[0]["candidate"]
