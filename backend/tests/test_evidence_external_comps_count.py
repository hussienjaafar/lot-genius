"""Test _count_external_comps function alignment with writer format."""


from lotgenius.evidence import _count_external_comps


def test_count_external_comps_num_comps_present():
    """Test that _count_external_comps uses num_comps when present."""
    item = {"sku_local": "TEST-001"}
    evidence_ledger = [
        {
            "source": "external_comps_summary",
            "external_comps_summary": {
                "num_comps": 4,
                "by_source": {"ebay": 3, "google_search": 1},
                "sample": [],
            },
        }
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 4, f"Expected count 4 from num_comps, got {count}"


def test_count_external_comps_by_source_fallback():
    """Test fallback to summing by_source when num_comps is missing."""
    item = {"sku_local": "TEST-002"}
    evidence_ledger = [
        {
            "source": "external_comps_summary",
            "external_comps_summary": {
                "by_source": {"ebay": 2, "google_search": 1},
                "sample": [],
            },
        }
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 3, f"Expected count 3 from by_source sum, got {count}"


def test_count_external_comps_missing_invalid_structure():
    """Test that invalid/missing structures return 0."""
    item = {"sku_local": "TEST-003"}

    # Case 1: Empty evidence ledger
    count = _count_external_comps(item, [], 180)
    assert count == 0, f"Expected count 0 for empty ledger, got {count}"

    # Case 2: None evidence ledger
    count = _count_external_comps(item, None, 180)
    assert count == 0, f"Expected count 0 for None ledger, got {count}"

    # Case 3: Evidence without external_comps_summary
    evidence_ledger = [{"source": "keepa", "data": {"price": 50.0}}]
    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 0, f"Expected count 0 for unrelated evidence, got {count}"

    # Case 4: Malformed external_comps_summary (not a dict)
    evidence_ledger = [{"external_comps_summary": "not a dict"}]
    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 0, f"Expected count 0 for malformed summary, got {count}"


def test_count_external_comps_invalid_num_comps():
    """Test that invalid num_comps values fall back to by_source."""
    item = {"sku_local": "TEST-004"}

    # Case 1: Non-numeric num_comps
    evidence_ledger = [
        {
            "external_comps_summary": {
                "num_comps": "invalid",
                "by_source": {"ebay": 2, "google_search": 1},
            }
        }
    ]
    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 3, f"Expected count 3 from by_source fallback, got {count}"

    # Case 2: Negative num_comps
    evidence_ledger = [
        {
            "external_comps_summary": {
                "num_comps": -1,
                "by_source": {"ebay": 1, "google_search": 2},
            }
        }
    ]
    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 3, f"Expected count 3 from by_source fallback, got {count}"


def test_count_external_comps_legacy_total_comps():
    """Test legacy fallback to total_comps when other fields missing."""
    item = {"sku_local": "TEST-005"}
    evidence_ledger = [{"external_comps_summary": {"total_comps": 5}}]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 5, f"Expected count 5 from total_comps legacy, got {count}"


def test_count_external_comps_multiple_evidence_records():
    """Test that multiple evidence records are summed correctly."""
    item = {"sku_local": "TEST-006"}
    evidence_ledger = [
        {"external_comps_summary": {"num_comps": 3, "by_source": {"ebay": 3}}},
        {"external_comps_summary": {"num_comps": 2, "by_source": {"google_search": 2}}},
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 5, f"Expected count 5 from summing multiple records, got {count}"


def test_count_external_comps_mixed_valid_invalid():
    """Test handling of mixed valid and invalid evidence records."""
    item = {"sku_local": "TEST-007"}
    evidence_ledger = [
        {"external_comps_summary": {"num_comps": 2, "by_source": {"ebay": 2}}},
        {"external_comps_summary": "invalid"},  # Should be skipped
        {"external_comps_summary": {"by_source": {"google_search": 1, "facebook": 1}}},
        {"unrelated_evidence": {"data": "ignored"}},  # Should be skipped
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 4, f"Expected count 4 from valid records only, got {count}"


def test_count_external_comps_by_source_with_non_numeric():
    """Test by_source handling with non-numeric values."""
    item = {"sku_local": "TEST-008"}
    evidence_ledger = [
        {
            "external_comps_summary": {
                "by_source": {
                    "ebay": 3,
                    "google_search": "invalid",  # Should be skipped
                    "facebook": 1.5,  # Float should work
                    "negative": -1,  # Negative should be skipped
                }
            }
        }
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    # Should count: ebay(3) + facebook(1.5 -> 1) = 4
    assert count == 4, f"Expected count 4 from valid by_source values, got {count}"


def test_count_external_comps_preference_order():
    """Test that num_comps is preferred over by_source even when both present."""
    item = {"sku_local": "TEST-009"}
    evidence_ledger = [
        {
            "external_comps_summary": {
                "num_comps": 10,  # This should be used
                "by_source": {"ebay": 3, "google_search": 1},  # This should be ignored
                "total_comps": 99,  # This should also be ignored
            }
        }
    ]

    count = _count_external_comps(item, evidence_ledger, 180)
    assert count == 10, f"Expected count 10 from num_comps preference, got {count}"
