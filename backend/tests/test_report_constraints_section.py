"""Test the consolidated Constraints section in report generation."""

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner
from lotgenius.cli.report_lot import main as cli


@pytest.fixture
def sample_items():
    """Sample items CSV data."""
    return pd.DataFrame(
        [
            {
                "sku_local": "X1",
                "est_price_mu": 60.0,
                "est_price_p50": 55.0,
                "sell_p60": 0.7,
            },
            {
                "sku_local": "X2",
                "est_price_mu": 40.0,
                "est_price_p50": 38.0,
                "sell_p60": 0.6,
            },
        ]
    )


def test_constraints_section_basic(tmp_path, sample_items):
    """Test basic Constraints section presence and content."""
    opt_data = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.82,
        "expected_cash_60d": 45.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "payout_lag_days": 14,
        "cashfloor": 100.0,
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check Constraints section exists
    assert "## Constraints" in md_content

    # Check required constraint bullets
    assert "- **ROI Target:** 1.25x" in md_content
    assert "- **Risk Threshold:** P(ROI>=target) >= 0.80" in md_content
    assert "- **Cashfloor:** $100.00" in md_content
    assert "- **Payout Lag:** 14 days" in md_content


def test_constraints_section_with_throughput(tmp_path, sample_items):
    """Test Constraints section with throughput constraint information."""
    opt_data = {
        "bid": 75.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "payout_lag_days": 14,
        "cashfloor": 50.0,
        "throughput": {
            "mins_per_unit": 5.0,
            "capacity_mins_per_day": 480.0,
            "total_minutes_required": 600.0,
            "available_minutes": 2880.0,
            "throughput_ok": True,
        },
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check Constraints section includes throughput
    assert "## Constraints" in md_content
    assert "- **Throughput Constraint:** Pass" in md_content


def test_constraints_section_throughput_fail(tmp_path, sample_items):
    """Test Constraints section shows throughput failure."""
    opt_data = {
        "bid": 75.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": {
            "throughput_ok": False,
        },
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    assert "- **Throughput Constraint:** Fail" in md_content


def test_constraints_section_with_gating(tmp_path, sample_items):
    """Test Constraints section with gating/hazmat counts."""
    opt_data = {
        "bid": 75.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "evidence_gate": {
            "evidence_summary": {
                "core_count": 150,
                "upside_count": 25,
                "total_items": 175,
                "gate_pass_rate": 0.857,
            }
        },
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check Constraints section includes gating counts
    assert "## Constraints" in md_content
    assert "- **Gated Items:** 150 core, 25 review" in md_content


def test_constraints_section_fallback_to_settings(tmp_path, sample_items):
    """Test Constraints section falls back to settings when values missing from opt."""
    opt_data = {
        "bid": 75.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        # payout_lag_days and cashfloor missing - should fallback to settings
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check Constraints section includes fallback values
    assert "## Constraints" in md_content
    # Should use settings defaults
    assert "- **Payout Lag:** 14 days" in md_content  # PAYOUT_LAG_DAYS default
    assert "- **Cashfloor:** $0.00" in md_content  # CASHFLOOR default


def test_constraints_section_missing_values(tmp_path, sample_items):
    """Test Constraints section handles missing ROI target and risk threshold."""
    opt_data = {
        "bid": 75.0,
        # roi_target and risk_threshold missing
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check Constraints section handles missing values
    assert "## Constraints" in md_content
    assert "- **ROI Target:** N/A" in md_content
    assert "- **Risk Threshold:** P(ROI>=target) >= N/A" in md_content


def test_ascii_safe_formatting(tmp_path, sample_items):
    """Test that all text is ASCII-safe without emojis or special symbols."""
    opt_data = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.82,
        "expected_cash_60d": 45.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    md_content = out_md.read_text(encoding="utf-8")

    # Check ASCII-safe formatting
    assert "1.35x" in md_content  # ratio uses 'x' not '×'
    assert "1.25x" in md_content
    assert ">=" in md_content  # uses >= not ≥
    assert "**PROCEED**" in md_content  # no emoji
    assert "**Meets All Constraints:** Yes" in md_content  # no emoji

    # Should not contain these non-ASCII characters
    assert "×" not in md_content
    assert "≥" not in md_content
    assert "✅" not in md_content
    assert "❌" not in md_content
    assert "🟢" not in md_content
    assert "🔴" not in md_content
    assert "🟡" not in md_content
