from backend.lotgenius.evidence import compute_evidence, evidence_to_dict


def test_two_source_gate_with_high_trust_id_included():
    # Test that items with high trust IDs are included in core
    ev = compute_evidence(
        item_key="SKU1",
        has_high_trust_id=True,
        sold_comps=[],
        secondary_signals={},
    )
    assert ev.include_in_core
    assert ev.review_reason is None


def test_two_source_gate_no_id_but_enough_comps_and_secondary_included():
    # Test that items without high trust ID but with enough comps and secondary signals are included
    ev = compute_evidence(
        item_key="SKU2",
        has_high_trust_id=False,
        sold_comps=[{"type": "keepa"}, {"type": "keepa"}, {"type": "keepa"}],  # 3 comps
        secondary_signals={"keepa_rank_trend": True},  # Has secondary signal
    )
    assert ev.include_in_core
    assert ev.review_reason is None


def test_two_source_gate_no_id_insufficient_comps_goes_to_review():
    # Test that items without high trust ID and insufficient comps go to review
    ev = compute_evidence(
        item_key="SKU3",
        has_high_trust_id=False,
        sold_comps=[{"type": "keepa"}],  # Only 1 comp
        secondary_signals={"keepa_rank_trend": True},
    )
    assert not ev.include_in_core
    assert "insufficient_comps" in ev.review_reason


def test_two_source_gate_no_secondary_signal_goes_to_review():
    # Test that items without secondary signals go to review (when REQUIRE_SECONDARY=True)
    ev = compute_evidence(
        item_key="SKU4",
        has_high_trust_id=False,
        sold_comps=[{"type": "keepa"}, {"type": "keepa"}, {"type": "keepa"}],  # 3 comps
        secondary_signals={},  # No secondary signals
    )
    assert not ev.include_in_core
    assert "no_secondary_signal" in ev.review_reason


def test_evidence_to_dict_includes_secondary_active():
    # Test that evidence_to_dict includes secondary_active field
    ev = compute_evidence(
        item_key="SKU5",
        has_high_trust_id=True,
        sold_comps=[],
        secondary_signals={"keepa_rank_trend": True, "keepa_offers_present": False},
    )
    d = evidence_to_dict(ev)
    assert "secondary_active" in d
    assert "keepa_rank_trend" in d["secondary_active"]
    assert "keepa_offers_present" not in d["secondary_active"]
