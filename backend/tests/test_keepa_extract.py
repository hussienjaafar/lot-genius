import json
from pathlib import Path

from lotgenius.keepa_extract import extract_stats_compact


def test_extract_stats_compact_with_stats():
    """Test that we can extract compact stats from fixture with stats field."""
    fixture_path = Path("backend/tests/fixtures/keepa/product_with_stats.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = extract_stats_compact(payload)

    # Check that all expected keys are present
    expected_keys = [
        "price_new_median",
        "price_used_median",
        "salesrank_median",
        "offers_count",
    ]
    assert all(k in result for k in expected_keys)

    # Check that stats values are extracted correctly from fixture
    assert result["price_new_median"] == 2575.50
    assert result["price_used_median"] == 2299.99
    assert result["salesrank_median"] == 125
    assert result["offers_count"] == 8


def test_extract_stats_compact_empty_payload():
    """Test defensive behavior with empty/null payload."""
    result = extract_stats_compact({})

    expected = {
        "price_new_median": None,
        "price_used_median": None,
        "salesrank_median": None,
        "offers_count": None,
    }
    assert result == expected


def test_extract_stats_compact_none_payload():
    """Test defensive behavior with None payload."""
    result = extract_stats_compact(None)

    expected = {
        "price_new_median": None,
        "price_used_median": None,
        "salesrank_median": None,
        "offers_count": None,
    }
    assert result == expected


def test_extract_stats_compact_no_products():
    """Test with payload that has no products array."""
    payload = {"tokensLeft": 100, "products": []}
    result = extract_stats_compact(payload)

    expected = {
        "price_new_median": None,
        "price_used_median": None,
        "salesrank_median": None,
        "offers_count": None,
    }
    assert result == expected


def test_extract_stats_compact_missing_stats():
    """Test with product that has no stats field."""
    payload = {
        "products": [
            {
                "asin": "B00TESTASIN",
                "title": "Test Product",
                "offers": 5,
                # No "stats" field
            }
        ]
    }
    result = extract_stats_compact(payload)

    # Should still extract offers from product root
    assert result["offers_count"] == 5
    assert result["price_new_median"] is None
    assert result["price_used_median"] is None
    assert result["salesrank_median"] is None


def test_extract_stats_compact_partial_stats():
    """Test with stats field that only has some values."""
    payload = {
        "products": [
            {
                "asin": "B00TESTASIN",
                "stats": {
                    "priceNewMedian": 1999.99,
                    # Missing priceUsedMedian and salesRankMedian
                },
                "offers": 3,
            }
        ]
    }
    result = extract_stats_compact(payload)

    assert result["price_new_median"] == 1999.99
    assert result["price_used_median"] is None
    assert result["salesrank_median"] is None
    assert result["offers_count"] == 3


def test_extract_stats_compact_offers_in_stats():
    """Test offers extraction from stats when not on product root."""
    payload = {
        "products": [
            {
                "asin": "B00TESTASIN",
                "stats": {"priceNewMedian": 2499.99, "offers": 7},
                # No offers on product root
            }
        ]
    }
    result = extract_stats_compact(payload)

    assert result["price_new_median"] == 2499.99
    assert result["offers_count"] == 7


def test_extract_stats_compact_malformed_numbers():
    """Test defensive handling of non-numeric values."""
    payload = {
        "products": [
            {
                "asin": "B00TESTASIN",
                "stats": {
                    "priceNewMedian": "invalid",
                    "priceUsedMedian": None,
                    "salesRankMedian": "",
                },
                "offers": "not_a_number",
            }
        ]
    }
    result = extract_stats_compact(payload)

    # All numeric fields should be None due to conversion failures
    assert result["price_new_median"] is None
    assert result["price_used_median"] is None
    assert result["salesrank_median"] is None
    assert result["offers_count"] == "not_a_number"  # offers is passed through as-is
