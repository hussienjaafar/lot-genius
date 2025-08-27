"""Test CLI optimize defaulting to CASHFLOOR when min_cash_60d is not provided."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from backend.cli.optimize_bid import main


@pytest.fixture
def sample_items_csv():
    """Create a minimal items CSV for testing."""
    data = {
        "est_price_mu": [25.0, 15.0],
        "est_price_sigma": [5.0, 3.0],
        "sell_p60": [0.8, 0.6],
        "quantity": [1, 1],  # Add quantity column to prevent the fillna error
    }
    df = pd.DataFrame(data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        return Path(f.name)


def test_cashfloor_default_in_cli(sample_items_csv, monkeypatch, tmp_path):
    """Test that CLI optimize uses settings.CASHFLOOR when --min-cash-60d is omitted."""
    # Set the environment variable for CASHFLOOR
    monkeypatch.setenv("CASHFLOOR", "123.0")

    # Force reload of settings to pick up the new environment variable
    import lotgenius.config
    from lotgenius.config import Settings

    import backend.cli.optimize_bid

    lotgenius.config.settings = Settings()
    # Also reload the CLI module's reference to settings
    backend.cli.optimize_bid.settings = lotgenius.config.settings

    runner = CliRunner()

    out_json = tmp_path / "test_optimize.json"
    evidence_out = tmp_path / "test_evidence.jsonl"

    try:
        result = runner.invoke(
            main,
            [
                str(sample_items_csv),
                "--out-json",
                str(out_json),
                "--lo",
                "10.0",
                "--hi",
                "50.0",
                "--evidence-out",
                str(evidence_out),
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()
        assert evidence_out.exists()

        # Check that the evidence meta contains the effective min_cash_60d
        evidence_content = evidence_out.read_text(encoding="utf-8")
        evidence_data = json.loads(evidence_content.strip())

        # The meta should contain min_cash_60d = 123.0 (from CASHFLOOR)
        assert evidence_data["meta"]["min_cash_60d"] == 123.0

        # Also verify the optimize result has reasonable output
        result_data = json.loads(out_json.read_text(encoding="utf-8"))
        assert "bid" in result_data
        assert "meets_constraints" in result_data

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)


def test_explicit_min_cash_overrides_cashfloor(sample_items_csv, monkeypatch, tmp_path):
    """Test that explicit --min-cash-60d overrides CASHFLOOR."""
    # Set the environment variable for CASHFLOOR
    monkeypatch.setenv("CASHFLOOR", "123.0")

    # Force reload of settings to pick up the new environment variable
    import lotgenius.config
    from lotgenius.config import Settings

    import backend.cli.optimize_bid

    lotgenius.config.settings = Settings()
    # Also reload the CLI module's reference to settings
    backend.cli.optimize_bid.settings = lotgenius.config.settings

    runner = CliRunner()

    out_json = tmp_path / "test_optimize.json"
    evidence_out = tmp_path / "test_evidence.jsonl"

    try:
        result = runner.invoke(
            main,
            [
                str(sample_items_csv),
                "--out-json",
                str(out_json),
                "--lo",
                "10.0",
                "--hi",
                "50.0",
                "--min-cash-60d",
                "456.0",  # Explicit value should override CASHFLOOR
                "--evidence-out",
                str(evidence_out),
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()
        assert evidence_out.exists()

        # Check that the evidence meta contains the explicit min_cash_60d
        evidence_content = evidence_out.read_text(encoding="utf-8")
        evidence_data = json.loads(evidence_content.strip())

        # The meta should contain min_cash_60d = 456.0 (explicit value, not CASHFLOOR)
        assert evidence_data["meta"]["min_cash_60d"] == 456.0

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)


def test_zero_cashfloor_default(sample_items_csv, monkeypatch, tmp_path):
    """Test that CASHFLOOR=0.0 works correctly."""
    # Set the environment variable for CASHFLOOR to 0.0
    monkeypatch.setenv("CASHFLOOR", "0.0")

    # Force reload of settings to pick up the new environment variable
    import lotgenius.config
    from lotgenius.config import Settings

    import backend.cli.optimize_bid

    lotgenius.config.settings = Settings()
    # Also reload the CLI module's reference to settings
    backend.cli.optimize_bid.settings = lotgenius.config.settings

    runner = CliRunner()

    out_json = tmp_path / "test_optimize.json"
    evidence_out = tmp_path / "test_evidence.jsonl"

    try:
        result = runner.invoke(
            main,
            [
                str(sample_items_csv),
                "--out-json",
                str(out_json),
                "--lo",
                "10.0",
                "--hi",
                "50.0",
                "--evidence-out",
                str(evidence_out),
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()
        assert evidence_out.exists()

        # Check that the evidence meta contains min_cash_60d = 0.0
        evidence_content = evidence_out.read_text(encoding="utf-8")
        evidence_data = json.loads(evidence_content.strip())

        # The meta should contain min_cash_60d = 0.0
        assert evidence_data["meta"]["min_cash_60d"] == 0.0

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
