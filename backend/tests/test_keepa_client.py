import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from lotgenius.keepa_client import KeepaClient, KeepaConfig, extract_primary_asin


@pytest.fixture
def keepa_config():
    """Test configuration with dummy API key"""
    return KeepaConfig(api_key="test_key", ttl_days=1)  # pragma: allowlist secret


@pytest.fixture
def keepa_response_ok():
    """Load test fixture for successful UPC lookup"""
    fixture_path = Path("backend/tests/fixtures/keepa/lookup_upc_ok.json")
    with open(fixture_path) as f:
        return json.load(f)


def test_keepa_client_init_with_config(keepa_config):
    """Test KeepaClient initialization with custom config"""
    client = KeepaClient(keepa_config)
    assert client.cfg.api_key == "test_key"  # pragma: allowlist secret
    assert client.cfg.ttl_days == 1


def test_keepa_client_init_from_settings():
    """Test KeepaClient initialization from settings"""
    with patch("lotgenius.keepa_client.settings") as mock_settings:
        mock_settings.KEEPA_API_KEY = "settings_key"  # pragma: allowlist secret
        mock_settings.KEEPA_CACHE_TTL_DAYS = 7

        client = KeepaClient()
        assert client.cfg.api_key == "settings_key"  # pragma: allowlist secret
        assert client.cfg.ttl_days == 7


def test_lookup_by_code_no_api_key():
    """Test that lookup fails gracefully when no API key is set"""
    config = KeepaConfig(api_key="", ttl_days=1)
    client = KeepaClient(config)

    result = client.lookup_by_code("123456789")
    assert result["ok"] is False
    assert "KEEPA_API_KEY not set" in result["error"]


@patch("lotgenius.keepa_client._cache_get")
@patch("lotgenius.keepa_client._cache_set")
def test_lookup_by_code_cached_hit(
    mock_cache_set, mock_cache_get, keepa_config, keepa_response_ok
):
    """Test that cached responses are returned without API call"""
    mock_cache_get.return_value = keepa_response_ok

    client = KeepaClient(keepa_config)
    result = client.lookup_by_code("841667147741")

    assert result["ok"] is True
    assert result["cached"] is True
    assert result["data"] == keepa_response_ok
    mock_cache_set.assert_not_called()


@patch("lotgenius.keepa_client._cache_get")
@patch("lotgenius.keepa_client._cache_set")
def test_lookup_by_code_api_success(
    mock_cache_set, mock_cache_get, keepa_config, keepa_response_ok
):
    """Test successful API call with caching"""
    mock_cache_get.return_value = None  # Cache miss

    # Mock successful HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = keepa_response_ok

    client = KeepaClient(keepa_config)

    with patch.object(client.session, "get", return_value=mock_response):
        result = client.lookup_by_code("841667147741")

    assert result["ok"] is True
    assert result["cached"] is False
    assert result["data"] == keepa_response_ok
    mock_cache_set.assert_called_once_with("product:1:841667147741", keepa_response_ok)


@patch("lotgenius.keepa_client._cache_get")
def test_lookup_by_code_api_error(mock_cache_get, keepa_config):
    """Test API error handling"""
    mock_cache_get.return_value = None  # Cache miss

    # Mock HTTP error response
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Invalid request"

    client = KeepaClient(keepa_config)

    with patch.object(client.session, "get", return_value=mock_response):
        result = client.lookup_by_code("invalid_code")

    assert result["ok"] is False
    assert result["status"] == 400
    assert result["error"] == "Invalid request"


@patch("lotgenius.keepa_client._cache_get")
def test_lookup_by_code_retry_logic(mock_cache_get, keepa_config):
    """Test retry logic for transient errors"""
    mock_cache_get.return_value = None  # Cache miss

    # Mock retry scenario: 429 then success
    mock_responses = [
        Mock(status_code=429),  # First attempt: rate limited
        Mock(status_code=200),  # Second attempt: success
    ]
    mock_responses[1].json.return_value = {"products": []}

    client = KeepaClient(keepa_config)

    with patch.object(client.session, "get", side_effect=mock_responses) as mock_get:
        with patch("time.sleep"):  # Skip actual sleep delays
            result = client.lookup_by_code("123")

    assert result["ok"] is True
    assert mock_get.call_count == 2


def test_search_by_title_stub(keepa_config):
    """Test that title search returns stub response"""
    client = KeepaClient(keepa_config)
    result = client.search_by_title("Echo Dot")

    assert result["ok"] is True
    assert result["cached"] is True
    assert "title-search stub" in result["data"]["note"]


def test_extract_primary_asin_success(keepa_response_ok):
    """Test ASIN extraction from successful response"""
    asin = extract_primary_asin(keepa_response_ok)
    assert asin == "B08N5WRWNW"


def test_extract_primary_asin_empty():
    """Test ASIN extraction from empty response"""
    asin = extract_primary_asin({"products": []})
    assert asin is None


def test_extract_primary_asin_invalid():
    """Test ASIN extraction from invalid data"""
    asin = extract_primary_asin({})
    assert asin is None

    asin = extract_primary_asin({"products": [{}]})
    assert asin is None
