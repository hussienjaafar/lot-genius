from backend.lotgenius.evidence import compute_evidence, evidence_to_dict


def test_review_items_listed_in_payload():
    # Test that review items are properly included in the evidence payload
    ev = compute_evidence(
        item_key="SKU4",
        has_high_trust_id=False,
        sold_comps=[],  # No comps
        secondary_signals={},  # No secondary signals
    )

    # Convert to dict to simulate what gets added to the payload
    ev_dict = evidence_to_dict(ev)

    # Check that the evidence dict has required fields
    assert "include_in_core" in ev_dict
    assert "review_reason" in ev_dict
    assert not ev_dict["include_in_core"]
    assert ev_dict["review_reason"] is not None


def test_evidence_summary_structure():
    # Test the structure of evidence summary
    evidence_summaries = []

    # Add a core item
    core_ev = compute_evidence(
        item_key="CORE1",
        has_high_trust_id=True,
        sold_comps=[],
        secondary_signals={},
    )
    evidence_summaries.append(evidence_to_dict(core_ev))

    # Add a review item
    review_ev = compute_evidence(
        item_key="REVIEW1",
        has_high_trust_id=False,
        sold_comps=[],
        secondary_signals={},
    )
    evidence_summaries.append(evidence_to_dict(review_ev))

    # Simulate the evidence_summary structure
    evidence_summary = {
        "core_items": sum(1 for e in evidence_summaries if e["include_in_core"]),
        "review_items": sum(1 for e in evidence_summaries if not e["include_in_core"]),
        "items": evidence_summaries,
    }

    # Verify structure
    assert evidence_summary["core_items"] == 1
    assert evidence_summary["review_items"] == 1
    assert len(evidence_summary["items"]) == 2
    assert all("include_in_core" in item for item in evidence_summary["items"])
    assert all("review_reason" in item for item in evidence_summary["items"])
