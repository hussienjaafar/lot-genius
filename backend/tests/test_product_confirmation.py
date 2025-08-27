
from lotgenius.evidence import EvidenceResult, evidence_to_dict
from lotgenius.scoring import product_confidence


def test_product_confidence_monotonicity():
    base = {
        "title_similarity": 0.0,
        "brand_match": False,
        "model_present": False,
        "price_z": 3.0,
        "sources_count": 0,
        "recency_days": 365,
        "high_trust_id": False,
    }

    s0 = product_confidence(base)

    # Increasing title similarity raises score
    s1 = product_confidence({**base, "title_similarity": 0.5})
    s2 = product_confidence({**base, "title_similarity": 1.0})
    assert s0 <= s1 <= s2

    # Brand match and model presence increase score
    sb = product_confidence({**base, "brand_match": True})
    sm = product_confidence({**base, "model_present": True})
    assert sb > s0
    assert sm > s0

    # Better price consistency (lower |z|) increases score
    sz2 = product_confidence({**base, "price_z": 2.0})
    sz1 = product_confidence({**base, "price_z": 1.0})
    sz0 = product_confidence({**base, "price_z": 0.0})
    assert s0 <= sz2 <= sz1 <= sz0

    # More sources increase score
    ss1 = product_confidence({**base, "sources_count": 1})
    ss2 = product_confidence({**base, "sources_count": 2})
    assert s0 <= ss1 <= ss2

    # More recent evidence increases score
    sr90 = product_confidence({**base, "recency_days": 90})
    sr30 = product_confidence({**base, "recency_days": 30})
    assert s0 <= sr90 <= sr30

    # High-trust ID increases score
    sid = product_confidence({**base, "high_trust_id": True})
    assert sid > s0


def test_product_confidence_bounds():
    # Extremely positive signals should not exceed 1.0
    signals = {
        "title_similarity": 1.0,
        "brand_match": True,
        "model_present": True,
        "price_z": 0.0,
        "sources_count": 5,
        "recency_days": 7,
        "high_trust_id": True,
    }
    s = product_confidence(signals)
    assert 0.0 <= s <= 1.0

    # Extremely negative signals should not be negative
    signals_neg = {
        "title_similarity": 0.0,
        "brand_match": False,
        "model_present": False,
        "price_z": 10.0,
        "sources_count": 0,
        "recency_days": 9999,
        "high_trust_id": False,
    }
    sneg = product_confidence(signals_neg)
    assert 0.0 <= sneg <= 1.0


def test_evidence_meta_included_roundtrip():
    # Create an EvidenceResult and ensure meta is preserved by evidence_to_dict
    ev = EvidenceResult(
        item_key="X",
        has_high_trust_id=True,
        sold_comp_count=4,
        lookback_days=180,
        secondary_signals={"keepa_offers_present": True},
        evidence_score=0.8,
        include_in_core=True,
        review_reason=None,
        sources={"keepa": True, "comps": 4},
        timestamp=0.0,
        meta={"product_confidence": 0.9},
    )
    d = evidence_to_dict(ev)
    assert "meta" in d
    assert isinstance(d["meta"], dict)
    assert d["meta"].get("product_confidence") == 0.9
