"""
Test cases for ID resolution precedence in lotgenius.resolve module.

Tests the new precedence logic: asin > upc > ean > canonical(upc_ean_asin)
and evidence ledger enrichment with identifier metadata.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
from lotgenius.resolve import resolve_ids


class TestResolverPrecedence:
    """Test ID resolution precedence and evidence ledger enrichment."""

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_precedence_prefers_explicit_asin_over_canonical(
        self, mock_parse, mock_client_class
    ):
        """Test that explicit ASIN field takes priority over canonical upc_ean_asin."""
        # Setup mock data - row has both explicit ASIN and canonical UPC
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-001",
                    "title": "Test Product",
                    "asin": "B012345678",  # Explicit ASIN field (10 chars)
                    "upc_ean_asin": "012345678905",  # Valid UPC in canonical
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Run resolver
        result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert ASIN was used directly without Keepa lookup
        assert result_df.iloc[0]["asin"] == "B012345678"
        assert result_df.iloc[0]["resolved_source"] == "direct:asin"

        # Assert no Keepa code lookup was called
        mock_client.lookup_by_code.assert_not_called()

        # Assert ledger has direct:asin record with correct metadata
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "direct:asin"
        assert record.ok == True
        assert record.match_asin == "B012345678"
        assert record.meta["identifier_source"] == "explicit:asin"
        assert record.meta["identifier_type"] == "asin"
        assert record.meta["identifier_used"] == "B012345678"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_precedence_uses_explicit_upc_when_no_asin(
        self, mock_parse, mock_client_class
    ):
        """Test that explicit UPC field is used when no ASIN present."""
        # Setup mock data - row has explicit UPC but no ASIN
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-002",
                    "title": "Test Product",
                    "upc": "012345678905",  # Valid UPC
                    "upc_ean_asin": "4006381333931",  # EAN in canonical (lower priority)
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful Keepa response
        mock_client.lookup_by_code.return_value = {
            "ok": True,
            "cached": False,
            "status": 200,
            "data": {"products": [{"asin": "B00FOUNDASIN"}]},
        }

        with patch(
            "lotgenius.resolve.extract_primary_asin", return_value="B00FOUNDASIN"
        ):
            result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert UPC was used for Keepa lookup
        assert result_df.iloc[0]["asin"] == "B00FOUNDASIN"
        assert result_df.iloc[0]["resolved_source"] == "keepa:code:fresh"

        # Assert Keepa was called with the explicit UPC (not the canonical EAN)
        mock_client.lookup_by_code.assert_called_once_with("012345678905")

        # Assert ledger metadata
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "keepa:code"
        assert record.meta["identifier_source"] == "explicit:upc"
        assert record.meta["identifier_type"] == "upc"
        assert record.meta["identifier_used"] == "012345678905"
        assert record.meta["code"] == "012345678905"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_precedence_uses_explicit_ean_when_no_asin_upc(
        self, mock_parse, mock_client_class
    ):
        """Test that explicit EAN field is used when no ASIN or UPC present."""
        # Setup mock data - row has explicit EAN
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-003",
                    "title": "Test Product",
                    "ean": "4006381333931",  # 13-digit EAN
                    "upc_ean_asin": "123456789012",  # UPC in canonical (lower priority)
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful Keepa response
        mock_client.lookup_by_code.return_value = {
            "ok": True,
            "cached": True,
            "status": 200,
            "data": {"products": [{"asin": "B00EANASIN"}]},
        }

        with patch("lotgenius.resolve.extract_primary_asin", return_value="B00EANASIN"):
            result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert EAN was used for Keepa lookup
        assert result_df.iloc[0]["asin"] == "B00EANASIN"
        assert result_df.iloc[0]["resolved_source"] == "keepa:code:cached"

        # Assert Keepa was called with the explicit EAN (not canonical UPC)
        mock_client.lookup_by_code.assert_called_once_with("4006381333931")

        # Assert ledger metadata
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "keepa:code"
        assert record.meta["identifier_source"] == "explicit:ean"
        assert record.meta["identifier_type"] == "ean"
        assert record.meta["identifier_used"] == "4006381333931"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_fallback_to_canonical_when_no_explicit_fields(
        self, mock_parse, mock_client_class
    ):
        """Test fallback to canonical upc_ean_asin when no explicit fields present."""
        # Setup mock data - only canonical field present
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-004",
                    "title": "Test Product",
                    "upc_ean_asin": "012345678905",  # Only canonical field
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful Keepa response
        mock_client.lookup_by_code.return_value = {
            "ok": True,
            "cached": False,
            "status": 200,
            "data": {"products": [{"asin": "B00CANONICAL"}]},
        }

        with patch(
            "lotgenius.resolve.extract_primary_asin", return_value="B00CANONICAL"
        ):
            result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert canonical field was used
        assert result_df.iloc[0]["asin"] == "B00CANONICAL"
        assert result_df.iloc[0]["resolved_source"] == "keepa:code:fresh"

        # Assert Keepa was called with canonical value
        mock_client.lookup_by_code.assert_called_once_with("012345678905")

        # Assert ledger metadata shows canonical source
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "keepa:code"
        assert record.meta["identifier_source"] == "canonical"
        assert record.meta["identifier_type"] == "upc"  # 12 digits = UPC
        assert record.meta["identifier_used"] == "012345678905"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_canonical_invalid_upc_but_explicit_valid_upc_wins(
        self, mock_parse, mock_client_class
    ):
        """Test explicit valid UPC wins over canonical invalid UPC."""
        # Setup mock data - invalid UPC in canonical, valid UPC in explicit
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-005",
                    "title": "Test Product",
                    "upc": "012345678905",  # Valid UPC (check digit 5)
                    "upc_ean_asin": "012345678901",  # Invalid UPC (check digit should be 5, not 1)
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful Keepa response for valid UPC
        mock_client.lookup_by_code.return_value = {
            "ok": True,
            "cached": True,
            "status": 200,
            "data": {"products": [{"asin": "B00VALIDUPC"}]},
        }

        with patch(
            "lotgenius.resolve.extract_primary_asin", return_value="B00VALIDUPC"
        ):
            result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert explicit valid UPC was used (not canonical invalid UPC)
        assert result_df.iloc[0]["asin"] == "B00VALIDUPC"
        assert result_df.iloc[0]["resolved_source"] == "keepa:code:cached"

        # Assert Keepa was called with explicit valid UPC
        mock_client.lookup_by_code.assert_called_once_with("012345678905")

        # Assert ledger metadata reflects explicit UPC source
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "keepa:code"
        assert record.meta["identifier_source"] == "explicit:upc"
        assert record.meta["identifier_type"] == "upc"
        assert record.meta["identifier_used"] == "012345678905"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_explicit_invalid_upc_falls_through_to_canonical(
        self, mock_parse, mock_client_class
    ):
        """Test that invalid explicit UPC is ignored and canonical is used."""
        # Setup mock data - invalid UPC in explicit, valid EAN in canonical
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-006",
                    "title": "Test Product",
                    "upc": "012345678901",  # Invalid UPC (wrong check digit)
                    "upc_ean_asin": "4006381333931",  # Valid EAN in canonical
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful Keepa response for canonical EAN
        mock_client.lookup_by_code.return_value = {
            "ok": True,
            "cached": False,
            "status": 200,
            "data": {"products": [{"asin": "B00CANONEAN"}]},
        }

        with patch(
            "lotgenius.resolve.extract_primary_asin", return_value="B00CANONEAN"
        ):
            result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert canonical EAN was used (invalid explicit UPC ignored)
        assert result_df.iloc[0]["asin"] == "B00CANONEAN"
        assert result_df.iloc[0]["resolved_source"] == "keepa:code:fresh"

        # Assert Keepa was called with canonical EAN, not invalid UPC
        mock_client.lookup_by_code.assert_called_once_with("4006381333931")

        # Assert ledger metadata reflects canonical source
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "keepa:code"
        assert record.meta["identifier_source"] == "canonical"
        assert record.meta["identifier_type"] == "ean"
        assert record.meta["identifier_used"] == "4006381333931"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_canonical_asin_precedence(self, mock_parse, mock_client_class):
        """Test that ASIN in canonical field is used directly."""
        # Setup mock data - ASIN in canonical field
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-007",
                    "title": "Test Product",
                    "upc_ean_asin": "B012345678",  # ASIN in canonical field (10 chars)
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result_df, ledger = resolve_ids("dummy.csv", use_network=True)

        # Assert ASIN was used directly without Keepa lookup
        assert result_df.iloc[0]["asin"] == "B012345678"
        assert result_df.iloc[0]["resolved_source"] == "direct:asin"

        # Assert no Keepa lookup was called
        mock_client.lookup_by_code.assert_not_called()

        # Assert ledger metadata
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "direct:asin"
        assert record.meta["identifier_source"] == "canonical"
        assert record.meta["identifier_type"] == "asin"
        assert record.meta["identifier_used"] == "B012345678"

    @patch("lotgenius.resolve.KeepaClient")
    @patch("lotgenius.resolve.parse_and_clean")
    def test_network_disabled_fallback_preserves_metadata(
        self, mock_parse, mock_client_class
    ):
        """Test that fallback with network disabled still includes metadata."""
        # Setup mock data
        df_mock = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-008",
                    "title": "Test Product",
                    "brand": "TestBrand",
                    "model": "TestModel",
                    "upc": "012345678905",  # Valid UPC but network disabled
                }
            ]
        )

        mock_parse.return_value = MagicMock(df_clean=df_mock)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result_df, ledger = resolve_ids("dummy.csv", use_network=False)

        # Assert no ASIN was resolved
        assert pd.isna(result_df.iloc[0]["asin"]) or result_df.iloc[0]["asin"] is None
        assert (
            pd.isna(result_df.iloc[0]["resolved_source"])
            or result_df.iloc[0]["resolved_source"] is None
        )

        # Assert fallback ledger entry includes metadata
        assert len(ledger) == 1
        record = ledger[0]
        assert record.source == "fallback:brand-model"
        assert record.ok == False
        assert record.meta["identifier_source"] == "fallback"
        assert record.meta["identifier_type"] == "unknown"
        assert record.meta["identifier_used"] == "TestBrand TestModel"
