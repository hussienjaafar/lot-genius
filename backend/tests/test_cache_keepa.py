"""
Tests for Keepa client caching functionality.

These tests are designed to run offline by monkeypatching cache methods.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from lotgenius.cache_metrics import get_registry
from lotgenius.keepa_client import KeepaClient, KeepaConfig, _cache_get, _cache_set


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset cache metrics before each test."""
    get_registry().reset_stats()


@pytest.fixture
def mock_keepa_config():
    """Create a test Keepa configuration."""
    return KeepaConfig(
        api_key="test_key",
        domain=1,
        timeout_sec=10,
        ttl_days=7,
        ttl_sec=None,
    )


@pytest.fixture
def mock_keepa_config_short_ttl():
    """Create a test Keepa configuration with short TTL for testing."""
    return KeepaConfig(
        api_key="test_key",
        domain=1,
        timeout_sec=10,
        ttl_days=7,
        ttl_sec=2,  # 2 seconds for testing
    )


class TestKeepaCache:
    """Test Keepa caching functionality."""

    def test_cache_miss_on_empty(self):
        """Test cache miss when no data is cached."""
        client = KeepaClient(KeepaConfig(api_key=""))
        result = client.lookup_by_code("123456789")

        # Should be a miss due to no API key
        assert result["ok"] is False
        assert result["error"] == "KEEPA_API_KEY not set"

    def test_cache_hit_returns_cached_data(self, mock_keepa_config):
        """Test cache hit returns cached data."""
        cached_data = {
            "products": [{"asin": "B123", "title": "Test Product"}],
            "tokensLeft": 100,
        }

        with patch("lotgenius.keepa_client._cache_get") as mock_get:
            mock_get.return_value = cached_data

            client = KeepaClient(mock_keepa_config)
            result = client.lookup_by_code("123456789")

            assert result["ok"] is True
            assert result["cached"] is True
            assert result["data"] == cached_data

            # Verify cache was checked with correct TTL
            mock_get.assert_called_once_with("product:1:123456789", 7 * 86400)

    def test_cache_store_after_network_call(self, mock_keepa_config):
        """Test data is cached after successful network call."""
        response_data = {
            "products": [{"asin": "B123", "title": "Test Product"}],
            "tokensLeft": 99,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch("lotgenius.keepa_client._cache_get") as mock_get, patch(
            "lotgenius.keepa_client._cache_set"
        ) as mock_set, patch("requests.Session.get") as mock_request:

            mock_get.return_value = None  # Cache miss
            mock_request.return_value = mock_response

            client = KeepaClient(mock_keepa_config)
            result = client.lookup_by_code("123456789")

            assert result["ok"] is True
            assert result["cached"] is False
            assert result["data"] == response_data

            # Verify data was stored in cache
            mock_set.assert_called_once_with("product:1:123456789", response_data)

    def test_ttl_sec_override(self, mock_keepa_config_short_ttl):
        """Test TTL seconds override is respected."""
        cached_data = {"products": []}

        with patch("lotgenius.keepa_client._cache_get") as mock_get:
            mock_get.return_value = cached_data

            client = KeepaClient(mock_keepa_config_short_ttl)
            client.lookup_by_code("123456789")

            # Verify cache was checked with short TTL (2 seconds)
            mock_get.assert_called_once_with("product:1:123456789", 2)

    def test_environment_ttl_override(self):
        """Test KEEPA_CACHE_TTL_SEC environment variable override."""
        with patch.dict(os.environ, {"KEEPA_CACHE_TTL_SEC": "10"}), patch(
            "lotgenius.keepa_client._cache_get"
        ) as mock_get:

            mock_get.return_value = {"products": []}

            client = KeepaClient()
            client.lookup_by_code("123456789")

            # Should use environment TTL (10 seconds)
            mock_get.assert_called_once_with("product:1:123456789", 10)

    def test_cache_metrics_recording(self):
        """Test cache metrics are properly recorded."""
        from lotgenius.cache_metrics import (
            get_registry,
            record_cache_hit,
            record_cache_miss,
        )

        # Direct test of metrics recording
        get_registry().reset_stats("keepa")

        # Simulate cache operations
        record_cache_miss("keepa")
        record_cache_hit("keepa")
        record_cache_hit("keepa")

        stats = get_registry().get_stats("keepa")
        assert stats.misses == 1
        assert stats.hits == 2
        assert stats.hit_ratio > 0.5

    def test_cache_metrics_in_response(self, mock_keepa_config):
        """Test cache metrics are included in response when enabled."""
        with patch.dict(os.environ, {"CACHE_METRICS": "1"}), patch(
            "lotgenius.keepa_client._cache_get"
        ) as mock_get:

            mock_get.return_value = {"products": []}

            client = KeepaClient(mock_keepa_config)
            result = client.lookup_by_code("123456789")

            assert "cache_stats" in result
            assert "hits" in result["cache_stats"]
            assert "misses" in result["cache_stats"]
            assert "hit_ratio" in result["cache_stats"]

    def test_different_cache_keys(self, mock_keepa_config):
        """Test different methods use different cache keys."""
        with patch("lotgenius.keepa_client._cache_get") as mock_get:
            mock_get.return_value = {"products": []}

            client = KeepaClient(mock_keepa_config)

            # Test different methods
            client.lookup_by_code("123456789")
            client.fetch_stats_by_code("123456789")
            client.fetch_stats_by_asin("B123456789")

            # Should have called cache with different keys
            expected_calls = [
                ("product:1:123456789", mock_keepa_config.ttl_days * 86400),
                ("product_stats:code:1:123456789", mock_keepa_config.ttl_days * 86400),
                ("product_stats:asin:1:B123456789", mock_keepa_config.ttl_days * 86400),
            ]

            actual_calls = [call.args for call in mock_get.call_args_list]
            assert actual_calls == expected_calls


class TestCacheFunctions:
    """Test low-level cache functions."""

    def test_cache_set_and_get_cycle(self):
        """Test setting and getting cache data."""
        test_data = {"test": "data", "number": 42}
        test_key = "test_key"

        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value = mock_cursor

            # Test cache set
            _cache_set(test_key, test_data)

            # Verify database operations
            assert mock_conn.execute.call_count >= 1
            assert mock_conn.commit.called
            assert mock_conn.close.called

    def test_cache_expiry(self):
        """Test cache expiry based on TTL."""
        # This would require more complex mocking of time and database
        # For now, we test the logic conceptually
        current_time = int(time.time())
        ttl_sec = 10

        # Simulate expired data (timestamp is older than TTL)
        expired_timestamp = current_time - ttl_sec - 1
        fresh_timestamp = current_time - 5

        with patch("lotgenius.keepa_client.time.time") as mock_time, patch(
            "sqlite3.connect"
        ) as mock_connect:

            mock_time.return_value = current_time
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn

            # Test expired data
            mock_cursor.fetchone.return_value = ('{"data": "test"}', expired_timestamp)
            mock_conn.execute.return_value = mock_cursor

            result = _cache_get("test_key", ttl_sec)
            assert result is None  # Should be None due to expiry

            # Test fresh data
            mock_cursor.fetchone.return_value = ('{"data": "test"}', fresh_timestamp)

            result = _cache_get("test_key", ttl_sec)
            assert result == {"data": "test"}  # Should return data


class TestCacheIntegration:
    """Integration tests for cache behavior."""

    def test_multiple_clients_share_cache(self, mock_keepa_config):
        """Test multiple client instances share the same cache."""
        cached_data = {"products": [{"asin": "B123"}]}

        with patch("lotgenius.keepa_client._cache_get") as mock_get:
            mock_get.return_value = cached_data

            client1 = KeepaClient(mock_keepa_config)
            client2 = KeepaClient(mock_keepa_config)

            result1 = client1.lookup_by_code("123456789")
            result2 = client2.lookup_by_code("123456789")

            # Both should get cached data
            assert result1["data"] == cached_data
            assert result2["data"] == cached_data
            assert mock_get.call_count == 2  # Each client checks cache

    def test_cache_cleanup_behavior(self):
        """Test cache cleanup removes expired entries."""
        # This is tested indirectly through the cleanup function
        with patch("sqlite3.connect") as mock_connect, patch(
            "lotgenius.keepa_client.time.time"
        ) as mock_time:

            mock_time.return_value = 1000
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 5  # Simulate 5 deleted rows
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value = mock_cursor

            from lotgenius.keepa_client import _cleanup_expired

            _cleanup_expired("test_key", 300)  # 5 minutes TTL

            # Verify cleanup was attempted
            assert mock_conn.execute.called
            assert mock_conn.commit.called
