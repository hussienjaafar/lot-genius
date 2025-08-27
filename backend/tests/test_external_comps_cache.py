"""Tests for external comps caching functionality."""

import time
from unittest.mock import patch

from backend.lotgenius.datasources import ebay_scraper
from backend.lotgenius.datasources.external_comps_cache import (
    _normalize_query_signature,
    clear_expired_cache,
    get_cached_comps,
    set_cached_comps,
)


def test_query_signature_normalization():
    """Test that query signatures are normalized consistently."""
    # Same inputs in different order should produce same signature
    sig1 = _normalize_query_signature(
        title="Logitech Mouse",
        brand="Logitech",
        model="M185",
        upc="123456",
        asin="B004YAVF8I",
        condition_hint="New",
    )

    sig2 = _normalize_query_signature(
        model="M185",
        title="Logitech Mouse",
        asin="B004YAVF8I",
        brand="Logitech",
        condition_hint="New",
        upc="123456",
    )

    assert sig1 == sig2

    # Different inputs should produce different signatures
    sig3 = _normalize_query_signature(
        title="Different Product",
        brand="Logitech",
    )

    assert sig1 != sig3

    # Case insensitive
    sig4 = _normalize_query_signature(
        title="LOGITECH MOUSE",
        brand="logitech",
        model="m185",
    )

    sig5 = _normalize_query_signature(
        title="logitech mouse",
        brand="Logitech",
        model="M185",
    )

    assert sig4 == sig5


def test_cache_set_and_get(tmp_path, monkeypatch):
    """Test basic cache set and get operations."""
    # Use temporary database for testing
    test_db = tmp_path / "test_cache.sqlite"
    monkeypatch.setattr(
        "backend.lotgenius.datasources.external_comps_cache._DB_PATH", test_db
    )

    test_comps = [
        {
            "source": "ebay",
            "title": "Test Product",
            "price": 25.99,
            "condition": "New",
            "sold_at": None,
            "url": "http://example.com",
            "id": None,
            "match_score": 0.8,
            "meta": {},
        }
    ]

    # Set cache
    set_cached_comps(
        source="ebay", comps_data=test_comps, title="Test Product", brand="TestBrand"
    )

    # Get from cache
    cached = get_cached_comps(source="ebay", title="Test Product", brand="TestBrand")

    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["title"] == "Test Product"
    assert cached[0]["price"] == 25.99


def test_cache_ttl_expiration(tmp_path, monkeypatch):
    """Test that cache respects TTL."""
    test_db = tmp_path / "test_cache.sqlite"
    monkeypatch.setattr(
        "backend.lotgenius.datasources.external_comps_cache._DB_PATH", test_db
    )

    # Set TTL to 1 second for testing
    monkeypatch.setattr(
        "backend.lotgenius.config.settings.EXTERNAL_COMPS_CACHE_TTL_DAYS", 1 / 86400
    )

    test_comps = [{"source": "ebay", "title": "Test", "price": 10.0}]

    # Set cache
    set_cached_comps(source="ebay", comps_data=test_comps, title="Test")

    # Should get cache immediately
    cached = get_cached_comps(source="ebay", title="Test")
    assert cached is not None

    # Wait for expiration
    time.sleep(2)

    # Should not get expired cache
    cached = get_cached_comps(source="ebay", title="Test")
    assert cached is None


def test_cache_different_sources():
    """Test that different sources are cached separately."""
    test_comps_ebay = [{"source": "ebay", "title": "eBay Item", "price": 20.0}]
    test_comps_google = [
        {"source": "google_search", "title": "Google Item", "price": 30.0}
    ]

    # Set cache for different sources with same query
    set_cached_comps(source="ebay", comps_data=test_comps_ebay, title="Same Query")

    set_cached_comps(
        source="google_search", comps_data=test_comps_google, title="Same Query"
    )

    # Get from cache
    cached_ebay = get_cached_comps(source="ebay", title="Same Query")
    cached_google = get_cached_comps(source="google_search", title="Same Query")

    assert cached_ebay is not None
    assert cached_google is not None
    assert cached_ebay[0]["title"] == "eBay Item"
    assert cached_google[0]["title"] == "Google Item"


def test_ebay_scraper_with_cache(monkeypatch):
    """Test that eBay scraper uses cache when available."""
    from datetime import datetime

    # Enable scrapers
    monkeypatch.setattr("backend.lotgenius.config.settings.ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr("backend.lotgenius.config.settings.SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(
        "backend.lotgenius.datasources.ebay_scraper.settings.ENABLE_EBAY_SCRAPER", True
    )
    monkeypatch.setattr(
        "backend.lotgenius.datasources.ebay_scraper.settings.SCRAPER_TOS_ACK", True
    )

    # Mock the cache to return data
    cached_data = [
        {
            "source": "ebay",
            "title": "Cached Item",
            "price": 15.99,
            "condition": "Used",
            "sold_at": datetime.now().isoformat(),
            "url": "http://cached.com",
            "id": None,
            "match_score": 0.9,
            "meta": {},
        }
    ]

    with patch(
        "backend.lotgenius.datasources.ebay_scraper.get_cached_comps"
    ) as mock_get_cache:
        mock_get_cache.return_value = cached_data

        # Mock requests.get to verify it's not called
        with patch(
            "backend.lotgenius.datasources.ebay_scraper.requests.get"
        ) as mock_requests:
            comps = ebay_scraper.fetch_sold_comps(query="Test Query", brand="TestBrand")

            # Should get cached data without making network request
            assert len(comps) == 1
            assert comps[0].title == "Cached Item"
            assert comps[0].price == 15.99
            mock_requests.assert_not_called()


def test_ebay_scraper_cache_miss(monkeypatch):
    """Test that eBay scraper fetches and caches on cache miss."""
    # Enable scrapers
    monkeypatch.setattr("backend.lotgenius.config.settings.ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr("backend.lotgenius.config.settings.SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(
        "backend.lotgenius.datasources.ebay_scraper.settings.ENABLE_EBAY_SCRAPER", True
    )
    monkeypatch.setattr(
        "backend.lotgenius.datasources.ebay_scraper.settings.SCRAPER_TOS_ACK", True
    )

    # Mock cache miss
    with patch(
        "backend.lotgenius.datasources.ebay_scraper.get_cached_comps"
    ) as mock_get_cache:
        mock_get_cache.return_value = None

        # Mock network response with proper HTML structure
        from datetime import datetime

        recent_date = datetime.now().strftime("%b %d, %Y")

        class MockResponse:
            status_code = 200
            text = f"""
            <li class="s-item">
                <div class="s-item__title">Network Item</div>
                <div class="s-item__price">$25.00</div>
                <a class="s-item__link" href="https://example.com/item1">Link</a>
                <div class="s-item__ended-date">{recent_date}</div>
            </li>
            """

            def raise_for_status(self):
                pass

        with patch(
            "backend.lotgenius.datasources.ebay_scraper.requests.get"
        ) as mock_requests:
            mock_requests.return_value = MockResponse()

            # Mock cache set
            with patch(
                "backend.lotgenius.datasources.ebay_scraper.set_cached_comps"
            ) as mock_set_cache:
                # Mock sleep
                with patch("backend.lotgenius.datasources.ebay_scraper._sleep_jitter"):
                    # Mock settings to reduce filtering strictness for this test
                    with patch(
                        "backend.lotgenius.datasources.ebay_scraper.settings"
                    ) as mock_settings:
                        mock_settings.SCRAPER_SIMILARITY_MIN = 0.1  # Very low threshold
                        mock_settings.SCRAPER_TOS_ACK = True
                        mock_settings.ENABLE_EBAY_SCRAPER = True

                        comps = ebay_scraper.fetch_sold_comps(
                            query="Test Query", brand="TestBrand"
                        )

                    # Should fetch from network
                    assert len(comps) == 1
                    assert comps[0].title == "Network Item"
                    assert comps[0].price == 25.0

                    # Should cache the results
                    mock_set_cache.assert_called_once()
                    cached_data = mock_set_cache.call_args[1]["comps_data"]
                    assert len(cached_data) == 1
                    assert cached_data[0]["title"] == "Network Item"


def test_clear_expired_cache(tmp_path, monkeypatch):
    """Test clearing expired cache entries."""
    test_db = tmp_path / "test_cache.sqlite"
    monkeypatch.setattr(
        "backend.lotgenius.datasources.external_comps_cache._DB_PATH", test_db
    )

    # Set TTL to 1 second
    monkeypatch.setattr(
        "backend.lotgenius.config.settings.EXTERNAL_COMPS_CACHE_TTL_DAYS", 1 / 86400
    )

    # Add multiple cache entries
    for i in range(3):
        set_cached_comps(
            source="ebay",
            comps_data=[{"title": f"Item {i}", "price": i * 10}],
            title=f"Query {i}",
        )

    # Wait for expiration
    time.sleep(2)

    # Add a fresh entry
    set_cached_comps(
        source="ebay",
        comps_data=[{"title": "Fresh Item", "price": 99}],
        title="Fresh Query",
    )

    # Clear expired
    deleted = clear_expired_cache()
    assert deleted == 3

    # Fresh entry should still exist
    cached = get_cached_comps(source="ebay", title="Fresh Query")
    assert cached is not None
    assert cached[0]["title"] == "Fresh Item"
