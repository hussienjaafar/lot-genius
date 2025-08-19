import json
from pathlib import Path

import pandas as pd
from cli.resolve_ids import main as resolve_cli
from click.testing import CliRunner
from lotgenius.resolve import enrich_keepa_stats


def _mock_keepa_client_for_stats(monkeypatch):
    """Patch KeepaClient to return our stats fixture."""
    stats_payload = json.loads(
        Path("backend/tests/fixtures/keepa/product_with_stats.json").read_text(
            encoding="utf-8"
        )
    )

    def fake_init(self, cfg=None):
        self.cfg = cfg or type(
            "C",
            (),
            {
                "api_key": "FAKE",  # pragma: allowlist secret
                "domain": 1,
                "timeout_sec": 5,
                "ttl_days": 7,
                "backoff_initial": 0.1,
                "backoff_max": 1.0,
                "max_retries": 1,
            },
        )
        self.session = None  # Not used in mock

        # Mock both stats methods
        def fake_fetch_stats_by_asin(asin):
            return {"ok": True, "cached": False, "data": stats_payload}

        def fake_fetch_stats_by_code(code):
            return {"ok": True, "cached": False, "data": stats_payload}

        self.fetch_stats_by_asin = fake_fetch_stats_by_asin
        self.fetch_stats_by_code = fake_fetch_stats_by_code

    monkeypatch.setattr("lotgenius.keepa_client.KeepaClient.__init__", fake_init)


def test_enrich_keepa_stats_with_asin(monkeypatch):
    """Test stats enrichment for a DataFrame with ASIN."""
    # Create test DataFrame with an ASIN
    df = pd.DataFrame(
        {
            "sku_local": ["SKU001"],
            "upc_ean_asin": ["123456789012"],
            "asin": ["B00TESTASIN"],
            "title": ["Test Product"],
        }
    )

    stats_payload = json.loads(
        Path("backend/tests/fixtures/keepa/product_with_stats.json").read_text(
            encoding="utf-8"
        )
    )

    def mock_client_init(self, cfg=None):
        self.cfg = cfg or type(
            "C", (), {"api_key": "FAKE", "domain": 1}  # pragma: allowlist secret
        )

        def fake_fetch_stats_by_asin(asin):
            return {"ok": True, "cached": False, "data": stats_payload}

        def fake_fetch_stats_by_code(code):
            return {"ok": True, "cached": False, "data": stats_payload}

        self.fetch_stats_by_asin = fake_fetch_stats_by_asin
        self.fetch_stats_by_code = fake_fetch_stats_by_code

    monkeypatch.setattr("lotgenius.keepa_client.KeepaClient.__init__", mock_client_init)

    result_df, evidence = enrich_keepa_stats(df, use_network=True)

    # Check that stats columns were added
    expected_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for col in expected_cols:
        assert col in result_df.columns

    # Check that stats values were populated
    assert result_df.iloc[0]["keepa_price_new_med"] == 2575.50
    assert result_df.iloc[0]["keepa_price_used_med"] == 2299.99
    assert result_df.iloc[0]["keepa_salesrank_med"] == 125
    assert result_df.iloc[0]["keepa_offers_count"] == 8

    # Check evidence record
    assert len(evidence) == 1
    assert evidence[0].source == "keepa:stats"
    assert evidence[0].ok is True
    assert evidence[0].match_asin == "B00TESTASIN"
    assert evidence[0].meta["via"] == "asin"


def test_enrich_keepa_stats_with_code_only(monkeypatch):
    """Test stats enrichment for a DataFrame with code but no ASIN."""
    df = pd.DataFrame(
        {
            "sku_local": ["SKU002"],
            "upc_ean_asin": ["123456789012"],
            "asin": [None],  # No ASIN
            "title": ["Test Product"],
        }
    )

    stats_payload = json.loads(
        Path("backend/tests/fixtures/keepa/product_with_stats.json").read_text(
            encoding="utf-8"
        )
    )

    def mock_client_init(self, cfg=None):
        self.cfg = cfg or type(
            "C", (), {"api_key": "FAKE", "domain": 1}  # pragma: allowlist secret
        )

        def fake_fetch_stats_by_asin(asin):
            return {"ok": True, "cached": False, "data": stats_payload}

        def fake_fetch_stats_by_code(code):
            return {"ok": True, "cached": False, "data": stats_payload}

        self.fetch_stats_by_asin = fake_fetch_stats_by_asin
        self.fetch_stats_by_code = fake_fetch_stats_by_code

    monkeypatch.setattr("lotgenius.keepa_client.KeepaClient.__init__", mock_client_init)

    result_df, evidence = enrich_keepa_stats(df, use_network=True)

    # Check that stats were populated via code lookup
    assert result_df.iloc[0]["keepa_price_new_med"] == 2575.50

    # Check evidence record shows code was used
    assert len(evidence) == 1
    assert evidence[0].meta["via"] == "code"


def test_enrich_keepa_stats_no_network():
    """Test that stats enrichment is skipped when use_network=False."""
    df = pd.DataFrame(
        {
            "sku_local": ["SKU003"],
            "asin": ["B00TESTASIN"],
        }
    )

    result_df, evidence = enrich_keepa_stats(df, use_network=False)

    # Should return original df with empty columns and no evidence
    expected_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for col in expected_cols:
        assert col in result_df.columns
        assert pd.isna(result_df.iloc[0][col])

    assert len(evidence) == 0


def test_enrich_keepa_stats_no_identifiers():
    """Test that rows without ASIN or valid code are skipped."""
    df = pd.DataFrame(
        {
            "sku_local": ["SKU004"],
            "upc_ean_asin": ["invalid"],  # Not a valid numeric code
            "asin": [None],
            "title": ["Test Product"],
        }
    )

    result_df, evidence = enrich_keepa_stats(df, use_network=True)

    # Stats columns should exist but be empty
    expected_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for col in expected_cols:
        assert col in result_df.columns
        assert pd.isna(result_df.iloc[0][col])

    # No evidence records should be created
    assert len(evidence) == 0


def test_cli_with_stats_flag(monkeypatch, tmp_path):
    """Test CLI --with-stats integration."""
    _mock_keepa_client_for_stats(monkeypatch)

    # Also need to mock the regular resolve logic
    def fake_resolve_ids(csv_path, threshold=88, use_network=True):
        df = pd.DataFrame(
            {
                "sku_local": ["SKU001"],
                "upc_ean_asin": ["123456789012"],
                "asin": ["B00TESTASIN"],
                "title": ["Test Product"],
                "resolved_source": ["direct:asin"],
            }
        )
        from datetime import datetime, timezone

        from lotgenius.resolve import EvidenceRecord

        ledger = [
            EvidenceRecord(
                row_index=0,
                sku_local="SKU001",
                upc_ean_asin="123456789012",
                source="direct:asin",
                ok=True,
                match_asin="B00TESTASIN",
                cached=True,
                meta={"note": "provided ASIN"},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        ]
        return df, ledger

    monkeypatch.setattr("cli.resolve_ids.resolve_ids", fake_resolve_ids)

    out_csv = tmp_path / "enriched.csv"
    out_ledger = tmp_path / "ledger.jsonl"

    runner = CliRunner()
    result = runner.invoke(
        resolve_cli,
        [
            "backend/tests/fixtures/manifest_multiqty.csv",  # Input CSV
            "--network",
            "--with-stats",  # Enable stats
            "--out-enriched",
            str(out_csv),
            "--out-ledger",
            str(out_ledger),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    # Check payload includes stats info
    assert payload["with_stats"] is True
    assert "stats_columns_present" in payload
    expected_stats_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for col in expected_stats_cols:
        assert col in payload["stats_columns_present"]

    # Check that CSV file contains stats columns
    assert out_csv.exists()
    result_df = pd.read_csv(out_csv)
    for col in expected_stats_cols:
        assert col in result_df.columns

    # Check that at least one row has stats data
    assert not pd.isna(result_df.iloc[0]["keepa_price_new_med"])


def test_cli_without_stats_flag(monkeypatch, tmp_path):
    """Test CLI without --with-stats (default behavior)."""
    _mock_keepa_client_for_stats(monkeypatch)

    # Mock regular resolve logic
    def fake_resolve_ids(csv_path, threshold=88, use_network=True):
        df = pd.DataFrame(
            {
                "sku_local": ["SKU001"],
                "asin": ["B00TESTASIN"],
                "resolved_source": ["direct:asin"],
            }
        )
        return df, []

    monkeypatch.setattr("cli.resolve_ids.resolve_ids", fake_resolve_ids)

    out_csv = tmp_path / "enriched.csv"
    out_ledger = tmp_path / "ledger.jsonl"

    runner = CliRunner()
    result = runner.invoke(
        resolve_cli,
        [
            "backend/tests/fixtures/manifest_multiqty.csv",
            "--network",
            # No --with-stats flag
            "--out-enriched",
            str(out_csv),
            "--out-ledger",
            str(out_ledger),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    # Check payload shows stats disabled
    assert payload["with_stats"] is False
    assert payload["stats_columns_present"] == []

    # Check CSV doesn't contain stats columns
    assert out_csv.exists()
    result_df = pd.read_csv(out_csv)
    stats_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for col in stats_cols:
        assert col not in result_df.columns
