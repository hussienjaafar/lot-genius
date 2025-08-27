"""Test CLI brand gating and hazmat policy functionality."""

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from backend.cli.optimize_bid import main as cli


@pytest.fixture
def sample_items_df():
    """Create sample items DataFrame with brands and hazmat indicators."""
    return pd.DataFrame(
        [
            {
                "sku_local": "APPLE_001",
                "est_price_mu": 100.0,
                "est_price_sigma": 15.0,
                "sell_p60": 0.8,
                "brand": "Apple",
                "is_hazmat": False,
            },
            {
                "sku_local": "SAMSUNG_002",
                "est_price_mu": 80.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.7,
                "brand": "Samsung",
                "is_hazmat": False,
            },
            {
                "sku_local": "BATTERY_003",
                "est_price_mu": 50.0,
                "est_price_sigma": 8.0,
                "sell_p60": 0.6,
                "brand": "Generic",
                "is_hazmat": True,
            },
        ]
    )


def test_cli_gated_brands_flag(sample_items_df, tmp_path, monkeypatch):
    """Test --gated-brands CLI flag functionality."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("GATED_BRANDS_CSV", "")

    # Run CLI with gated brands
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--gated-brands",
            "Apple,Samsung",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert "out_json" in payload
    assert Path(payload["out_json"]).exists()

    # Verify JSON output contains optimization results
    opt_result = json.loads(Path(out_json).read_text())
    assert "bid" in opt_result
    assert "roi_p50" in opt_result


def test_cli_hazmat_policy_exclude(sample_items_df, tmp_path, monkeypatch):
    """Test --hazmat-policy exclude functionality."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("HAZMAT_POLICY", "allow")

    # Run CLI with hazmat policy exclude
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--hazmat-policy",
            "exclude",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert Path(payload["out_json"]).exists()


def test_cli_hazmat_policy_review(sample_items_df, tmp_path, monkeypatch):
    """Test --hazmat-policy review functionality."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("HAZMAT_POLICY", "allow")

    # Run CLI with hazmat policy review
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--hazmat-policy",
            "review",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert Path(payload["out_json"]).exists()


def test_cli_hazmat_policy_allow(sample_items_df, tmp_path, monkeypatch):
    """Test --hazmat-policy allow functionality."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("HAZMAT_POLICY", "exclude")

    # Run CLI with hazmat policy allow
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--hazmat-policy",
            "allow",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert Path(payload["out_json"]).exists()


def test_cli_combined_gating_policies(sample_items_df, tmp_path, monkeypatch):
    """Test combined --gated-brands and --hazmat-policy flags."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("GATED_BRANDS_CSV", "")
    monkeypatch.setenv("HAZMAT_POLICY", "allow")

    # Run CLI with both policies
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--gated-brands",
            "Apple",
            "--hazmat-policy",
            "exclude",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert Path(payload["out_json"]).exists()


def test_cli_gating_with_evidence_output(sample_items_df, tmp_path, monkeypatch):
    """Test gating policies with evidence output."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    evidence_out = tmp_path / "evidence.jsonl"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("GATED_BRANDS_CSV", "")
    monkeypatch.setenv("HAZMAT_POLICY", "allow")

    # Run CLI with evidence output
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--evidence-out",
            str(evidence_out),
            "--lo",
            "0",
            "--hi",
            "200",
            "--gated-brands",
            "Apple,Samsung",
            "--hazmat-policy",
            "review",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify evidence file was created
    payload = json.loads(res.output)
    assert payload["evidence_out"] == str(evidence_out)
    assert Path(evidence_out).exists()

    # Verify evidence content includes gating metadata
    evidence_content = Path(evidence_out).read_text()
    evidence_record = json.loads(evidence_content.strip())

    assert "meta" in evidence_record
    meta = evidence_record["meta"]
    assert "sims" in meta
    assert "roi_target" in meta


def test_cli_gating_invalid_hazmat_policy(sample_items_df, tmp_path):
    """Test CLI with invalid hazmat policy value."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Run CLI with invalid hazmat policy
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--hazmat-policy",
            "invalid",
            "--sims",
            "100",
        ],
    )

    # Should fail with invalid choice
    assert res.exit_code != 0
    assert "Invalid value for '--hazmat-policy'" in res.output


def test_cli_empty_gated_brands(sample_items_df, tmp_path, monkeypatch):
    """Test CLI with empty gated brands string."""
    in_csv = tmp_path / "items.csv"
    out_json = tmp_path / "opt.json"
    sample_items_df.to_csv(in_csv, index=False)

    # Set environment to ensure clean state
    monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")

    # Run CLI with empty gated brands (should override settings)
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--gated-brands",
            "",
            "--sims",
            "100",
        ],
    )

    assert res.exit_code == 0, res.output

    # Verify output structure
    payload = json.loads(res.output)
    assert "recommended_bid" in payload
    assert Path(payload["out_json"]).exists()
