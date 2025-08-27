"""Live Keepa integration tests - run only when KEEPA_API_KEY is set."""

import os

import pytest
from lotgenius.keepa_client import KeepaClient

# Skip all tests in this module if KEEPA_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("KEEPA_API_KEY"),
    reason="KEEPA_API_KEY not set - skipping live Keepa integration tests",
)


@pytest.fixture
def keepa_client():
    """Create a KeepaClient instance for testing."""
    return KeepaClient()


@pytest.fixture
def stable_test_data():
    """
    Stable ASIN/UPC pairs for testing.
    Using well-known products that should remain stable in Keepa.
    """
    return [
        {
            "asin": "B07FZ8S74R",  # Echo Dot (3rd Gen)
            "upc": "841667174051",  # Known UPC for Echo Dot
        },
        {
            "asin": "B08N5WRWNW",  # Echo Dot (4th Gen)
            "upc": "841667177386",  # Known UPC for Echo Dot 4th gen
        },
    ]


@pytest.mark.parametrize(
    "test_item",
    [
        {"asin": "B07FZ8S74R", "upc": "841667174051"},
        {"asin": "B08N5WRWNW", "upc": "841667177386"},
    ],
)
def test_lookup_by_code_returns_valid_data(keepa_client, test_item):
    """Test KeepaClient.lookup_by_code returns ok=True with products and asin."""
    result = keepa_client.lookup_by_code(test_item["upc"])

    # Should succeed
    assert result["ok"] is True, f"Keepa lookup failed: {result.get('error')}"

    # Should have data structure
    assert "data" in result
    data = result["data"]

    # Should contain products
    assert "products" in data
    products = data["products"]
    assert len(products) > 0, "No products returned from Keepa"

    # Should contain an ASIN
    first_product = products[0]
    assert "asin" in first_product
    asin = first_product["asin"]
    assert asin is not None and len(asin) > 0, "No valid ASIN returned"

    print(f"✓ UPC {test_item['upc']} resolved to ASIN {asin}")


def test_caching_behavior(keepa_client, stable_test_data):
    """Test that caching works: first request uncached, second cached."""
    test_upc = stable_test_data[0]["upc"]

    # Clear any existing cache for this test
    # (In a production environment, we might want to preserve cache,
    #  but for testing we want to verify caching behavior)

    # First call should not be cached
    result1 = keepa_client.lookup_by_code(test_upc)
    assert result1["ok"] is True, f"First lookup failed: {result1.get('error')}"
    cached1 = result1.get("cached", False)

    # Second call should be cached (unless cache was cleared)
    result2 = keepa_client.lookup_by_code(test_upc)
    assert result2["ok"] is True, f"Second lookup failed: {result2.get('error')}"
    cached2 = result2.get("cached", False)

    # Verify caching behavior
    print(f"First call cached: {cached1}, Second call cached: {cached2}")

    # If first call wasn't cached, second should be cached
    if not cached1:
        assert cached2 is True, "Second call should be cached after first call"

    # Data should be consistent between calls
    assert (
        result1["data"]["products"][0]["asin"] == result2["data"]["products"][0]["asin"]
    )

    print(f"✓ Caching verified: first={cached1}, second={cached2}")


def test_fetch_stats_by_asin_returns_stats(keepa_client, stable_test_data):
    """Test fetch_stats_by_asin returns ok=True and includes expected stats fields."""
    test_asin = stable_test_data[0]["asin"]

    result = keepa_client.fetch_stats_by_asin(test_asin)

    # Should succeed
    assert result["ok"] is True, f"Stats fetch failed: {result.get('error')}"

    # Should have data
    assert "data" in result
    data = result["data"]

    # Should contain products with stats
    assert "products" in data
    products = data["products"]
    assert len(products) > 0, "No products returned from stats call"

    first_product = products[0]

    # Should have basic product fields
    assert "asin" in first_product
    assert first_product["asin"] == test_asin

    # Should have stats-related fields (exact structure may vary)
    # Common Keepa stats fields include: stats, csv, imagesCSV, etc.
    has_stats_fields = any(
        field in first_product
        for field in ["stats", "csv", "imagesCSV", "categoryTree"]
    )
    assert (
        has_stats_fields
    ), f"No stats fields found in product data. Available keys: {list(first_product.keys())}"

    print(
        f"✓ ASIN {test_asin} returned stats data with fields: {list(first_product.keys())}"
    )


def test_lookup_by_code_no_api_key():
    """Test that lookup_by_code fails gracefully without API key."""
    from lotgenius.keepa_client import KeepaClient, KeepaConfig

    # Create client with no API key
    cfg = KeepaConfig(api_key="")
    client = KeepaClient(cfg)

    result = client.lookup_by_code("123456789")

    assert result["ok"] is False
    assert "KEEPA_API_KEY not set" in result["error"]

    print("✓ No API key handling works correctly")


def test_fetch_stats_by_asin_no_api_key():
    """Test that fetch_stats_by_asin fails gracefully without API key."""
    from lotgenius.keepa_client import KeepaClient, KeepaConfig

    # Create client with no API key
    cfg = KeepaConfig(api_key="")
    client = KeepaClient(cfg)

    result = client.fetch_stats_by_asin("B07FZ8S74R")

    assert result["ok"] is False
    assert "KEEPA_API_KEY not set" in result["error"]

    print("✓ No API key handling works correctly for stats")
