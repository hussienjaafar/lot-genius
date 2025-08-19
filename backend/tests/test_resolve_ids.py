from unittest.mock import Mock, patch

import pytest
from cli.resolve_ids import resolve_ids
from click.testing import CliRunner
from lotgenius.resolve import resolve_dataframe, resolve_item_to_asin
from lotgenius.schema import Item


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing"""
    return """title,brand,upc,quantity
Echo Dot,Amazon,841667147741,1
iPhone 13,Apple,194252707123,2
Unknown Product,,123456789,1"""


@pytest.fixture
def temp_csv(tmp_path, sample_csv_content):
    """Create temporary CSV file for testing"""
    csv_file = tmp_path / "test_manifest.csv"
    csv_file.write_text(sample_csv_content)
    return csv_file


@pytest.fixture
def mock_keepa_client():
    """Mock KeepaClient for testing"""
    client = Mock()

    # Mock successful lookup for Echo Dot UPC
    def mock_lookup(code):
        if code == "841667147741":
            return {
                "ok": True,
                "cached": False,
                "data": {"products": [{"asin": "B08N5WRWNW"}]},
            }
        else:
            return {"ok": False, "error": "Product not found"}

    client.lookup_by_code = mock_lookup
    client.search_by_title.return_value = {
        "ok": True,
        "cached": True,
        "data": {"products": [], "note": "title-search stub"},
    }

    return client


def test_resolve_item_to_asin_success(mock_keepa_client):
    """Test successful item resolution"""
    item = Item(title="Echo Dot", upc_ean_asin="841667147741")

    result = resolve_item_to_asin(item, mock_keepa_client)

    assert result.success is True
    assert result.asin == "B08N5WRWNW"
    assert len(result.evidence) >= 1
    assert result.evidence[0].source == "keepa_lookup"
    assert result.evidence[0].success is True


def test_resolve_item_to_asin_fallback(mock_keepa_client):
    """Test fallback to title search when UPC lookup fails"""
    item = Item(title="Unknown Product", upc_ean_asin="123456789")

    result = resolve_item_to_asin(item, mock_keepa_client)

    assert result.success is False
    assert result.asin is None
    assert len(result.evidence) >= 2  # UPC lookup + title search
    assert any(e.source == "keepa_lookup" for e in result.evidence)
    assert any(e.source == "title_search_stub" for e in result.evidence)


def test_resolve_item_to_asin_no_identifiers():
    """Test resolution with no identifiers"""
    item = Item(title="Generic Product")

    with patch("lotgenius.resolve.KeepaClient") as mock_client_class:
        mock_client = Mock()
        mock_client.search_by_title.return_value = {
            "ok": True,
            "cached": True,
            "data": {"products": [], "note": "title-search stub"},
        }
        mock_client_class.return_value = mock_client

        result = resolve_item_to_asin(item)

        assert result.success is False
        assert result.asin is None
        assert len(result.evidence) == 1
        assert result.evidence[0].source == "title_search_stub"


def test_resolve_dataframe(mock_keepa_client):
    """Test DataFrame resolution"""
    import pandas as pd

    df = pd.DataFrame(
        [
            {"title": "Echo Dot", "upc_ean_asin": "841667147741"},
            {"title": "iPhone 13", "upc_ean_asin": "194252707123"},
            {"title": "Unknown", "upc_ean_asin": "123456789"},
        ]
    )

    enriched_df, evidence_ledger = resolve_dataframe(df, mock_keepa_client)

    # Check enriched DataFrame
    assert "resolved_asin" in enriched_df.columns
    assert enriched_df.loc[0, "resolved_asin"] == "B08N5WRWNW"  # Echo Dot resolved
    assert pd.isna(enriched_df.loc[1, "resolved_asin"])  # iPhone not found
    assert pd.isna(enriched_df.loc[2, "resolved_asin"])  # Unknown not found

    # Check evidence ledger
    assert len(evidence_ledger) >= 3  # At least one entry per row
    assert all("row_index" in entry for entry in evidence_ledger)
    assert all("source" in entry for entry in evidence_ledger)


@patch("lotgenius.resolve.KeepaClient")
@patch("lotgenius.parse.parse_and_clean")
def test_cli_resolve_ids_basic(mock_parse, mock_client_class, temp_csv):
    """Test basic CLI functionality"""
    # Mock parse_and_clean result
    import pandas as pd

    mock_result = Mock()
    mock_result.df_clean = pd.DataFrame(
        [{"title": "Echo Dot", "upc_ean_asin": "841667147741", "condition": "New"}]
    )
    mock_result.df_exploded = None
    mock_result.unmapped_headers = []
    mock_parse.return_value = mock_result

    # Mock KeepaClient
    mock_client = Mock()
    mock_client.cfg.api_key = "test_key"  # pragma: allowlist secret
    mock_client_class.return_value = mock_client

    # Mock resolve_dataframe
    with patch("cli.resolve_ids.resolve_dataframe") as mock_resolve:
        enriched_df = pd.DataFrame(
            [
                {
                    "title": "Echo Dot",
                    "upc_ean_asin": "841667147741",
                    "resolved_asin": "B08N5WRWNW",
                }
            ]
        )
        evidence = [{"row_index": 0, "source": "keepa_lookup", "success": True}]
        mock_resolve.return_value = (enriched_df, evidence)

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(resolve_ids, [str(temp_csv)])

            assert result.exit_code == 0
            assert "Resolution complete!" in result.output


@patch("lotgenius.resolve.KeepaClient")
def test_cli_resolve_ids_no_api_key(mock_client_class, temp_csv):
    """Test CLI behavior when no API key is configured"""
    mock_client = Mock()
    mock_client.cfg.api_key = ""
    mock_client_class.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(resolve_ids, [str(temp_csv)])

    assert "Warning: No Keepa API key configured" in result.output


def test_cli_resolve_ids_custom_paths(temp_csv):
    """Test CLI with custom output paths"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        output_csv = "custom_output.csv"
        output_ledger = "custom_ledger.jsonl"

        with patch("cli.resolve_ids.parse_and_clean"), patch(
            "cli.resolve_ids.resolve_dataframe"
        ) as mock_resolve, patch("cli.resolve_ids.KeepaClient"):

            import pandas as pd

            mock_resolve.return_value = (
                pd.DataFrame([{"title": "test", "resolved_asin": None}]),
                [],
            )

            result = runner.invoke(
                resolve_ids,
                [
                    str(temp_csv),
                    "--output-csv",
                    output_csv,
                    "--output-ledger",
                    output_ledger,
                ],
            )

            assert result.exit_code == 0
            assert f"Output CSV: {output_csv}" in result.output
            assert f"Output ledger: {output_ledger}" in result.output


def test_cli_resolve_ids_with_explode_option(temp_csv):
    """Test CLI with explode option"""
    runner = CliRunner()

    with patch("cli.resolve_ids.parse_and_clean") as mock_parse, patch(
        "cli.resolve_ids.resolve_dataframe"
    ) as mock_resolve, patch("cli.resolve_ids.KeepaClient"):

        import pandas as pd

        # Mock parse result with exploded DataFrame
        mock_result = Mock()
        mock_result.df_clean = pd.DataFrame([{"title": "test"}])
        mock_result.df_exploded = pd.DataFrame(
            [{"title": "test", "unit_index": 1}, {"title": "test", "unit_index": 2}]
        )
        mock_result.unmapped_headers = []
        mock_parse.return_value = mock_result

        mock_resolve.return_value = (mock_result.df_exploded, [])

        runner.invoke(resolve_ids, [str(temp_csv), "--explode"])

        # Verify parse_and_clean was called with explode=True
        mock_parse.assert_called_once()
        args, kwargs = mock_parse.call_args
        assert kwargs["explode"] is True


def test_evidence_ledger_format():
    """Test that evidence ledger entries have required fields"""
    import pandas as pd
    from lotgenius.resolve import resolve_dataframe

    df = pd.DataFrame(
        [{"title": "Test Product", "upc_ean_asin": "123456789", "condition": "New"}]
    )

    with patch("lotgenius.resolve.KeepaClient") as mock_client_class:
        mock_client = Mock()
        mock_client.lookup_by_code.return_value = {"ok": False, "error": "Not found"}
        mock_client.search_by_title.return_value = {
            "ok": True,
            "data": {"products": [], "note": "stub"},
        }
        mock_client_class.return_value = mock_client

        _, evidence_ledger = resolve_dataframe(df)

        # Check that each evidence entry has required fields
        required_fields = [
            "row_index",
            "source",
            "timestamp",
            "raw",
            "asin",
            "success",
            "item_title",
            "item_upc_ean_asin",
        ]

        for entry in evidence_ledger:
            for field in required_fields:
                assert field in entry, f"Missing field {field} in evidence entry"
