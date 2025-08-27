"""Test throughput section rendering in report_lot CLI."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner
from lotgenius.cli.report_lot import _mk_markdown

from backend.cli.report_lot import main as report_main


@pytest.fixture
def sample_items_csv():
    """Create a minimal items CSV for testing."""
    data = {
        "est_price_mu": [25.0, 15.0],
        "est_price_sigma": [5.0, 3.0],
        "sell_p60": [0.8, 0.6],
        "quantity": [1, 1],
    }
    df = pd.DataFrame(data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        return Path(f.name)


@pytest.fixture
def opt_json_with_throughput():
    """Create optimizer result JSON with throughput data."""
    opt_data = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": {
            "mins_per_unit": 5.0,
            "capacity_mins_per_day": 480.0,
            "total_minutes_required": 10.0,
            "available_minutes": 28800.0,  # 480 * 60 days
            "throughput_ok": True,
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(opt_data, f, indent=2)
        return Path(f.name)


@pytest.fixture
def opt_json_throughput_fail():
    """Create optimizer result JSON with failing throughput."""
    opt_data = {
        "bid": 25.0,
        "roi_p50": 0.95,
        "prob_roi_ge_target": 0.30,
        "expected_cash_60d": 45.0,
        "meets_constraints": False,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": {
            "mins_per_unit": 20.0,
            "capacity_mins_per_day": 5.0,
            "total_minutes_required": 40.0,
            "available_minutes": 300.0,  # 5 * 60 days
            "throughput_ok": False,
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(opt_data, f, indent=2)
        return Path(f.name)


@pytest.fixture
def opt_json_no_throughput():
    """Create optimizer result JSON without throughput data."""
    opt_data = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(opt_data, f, indent=2)
        return Path(f.name)


def test_report_throughput_pass_rendering(
    sample_items_csv, opt_json_with_throughput, tmp_path
):
    """Test report rendering with passing throughput constraints."""
    runner = CliRunner()

    out_markdown = tmp_path / "test_report.md"

    try:
        result = runner.invoke(
            report_main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(opt_json_with_throughput),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_markdown.exists()

        # Check report content
        markdown_content = out_markdown.read_text(encoding="utf-8")

        # Should contain Throughput section
        assert "## Throughput" in markdown_content
        assert "- **Mins per unit:** 5.0" in markdown_content
        assert "- **Capacity mins/day:** 480.0" in markdown_content
        assert "- **Total mins required (lot):** 10.0" in markdown_content
        assert "- **Available mins (horizon):** 28800.0" in markdown_content
        assert "- **Throughput OK:** Yes" in markdown_content

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        opt_json_with_throughput.unlink(missing_ok=True)


def test_report_throughput_fail_rendering(
    sample_items_csv, opt_json_throughput_fail, tmp_path
):
    """Test report rendering with failing throughput constraints."""
    runner = CliRunner()

    out_markdown = tmp_path / "test_report.md"

    try:
        result = runner.invoke(
            report_main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(opt_json_throughput_fail),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_markdown.exists()

        # Check report content
        markdown_content = out_markdown.read_text(encoding="utf-8")

        # Should contain Throughput section with failure
        assert "## Throughput" in markdown_content
        assert "- **Mins per unit:** 20.0" in markdown_content
        assert "- **Capacity mins/day:** 5.0" in markdown_content
        assert "- **Total mins required (lot):** 40.0" in markdown_content
        assert "- **Available mins (horizon):** 300.0" in markdown_content
        assert "- **Throughput OK:** No" in markdown_content

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        opt_json_throughput_fail.unlink(missing_ok=True)


def test_report_no_throughput_section(
    sample_items_csv, opt_json_no_throughput, tmp_path
):
    """Test report rendering without throughput data."""
    runner = CliRunner()

    out_markdown = tmp_path / "test_report.md"

    try:
        result = runner.invoke(
            report_main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(opt_json_no_throughput),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_markdown.exists()

        # Check report content
        markdown_content = out_markdown.read_text(encoding="utf-8")

        # Should NOT contain Throughput section
        assert "## Throughput" not in markdown_content
        assert "Throughput OK" not in markdown_content

        # But should still have other sections
        assert "## Executive Summary" in markdown_content
        assert "## Optimization Parameters" in markdown_content
        assert "## Investment Decision" in markdown_content

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        opt_json_no_throughput.unlink(missing_ok=True)


def test_mk_markdown_throughput_direct():
    """Test _mk_markdown function directly with throughput data."""
    items = pd.DataFrame(
        {
            "est_price_mu": [25.0, 15.0],
            "est_price_sigma": [5.0, 3.0],
            "sell_p60": [0.8, 0.6],
        }
    )

    opt_with_throughput = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": {
            "mins_per_unit": 5.0,
            "capacity_mins_per_day": 480.0,
            "total_minutes_required": 10.0,
            "available_minutes": 28800.0,
            "throughput_ok": True,
        },
    }

    markdown = _mk_markdown(items, opt_with_throughput)

    # Should contain Throughput section
    assert "## Throughput" in markdown
    assert "**Mins per unit:** 5.0" in markdown
    assert "**Capacity mins/day:** 480.0" in markdown
    assert "**Total mins required (lot):** 10.0" in markdown
    assert "**Available mins (horizon):** 28800.0" in markdown
    assert "**Throughput OK:** Yes" in markdown


def test_mk_markdown_no_throughput_direct():
    """Test _mk_markdown function directly without throughput data."""
    items = pd.DataFrame(
        {
            "est_price_mu": [25.0, 15.0],
            "est_price_sigma": [5.0, 3.0],
            "sell_p60": [0.8, 0.6],
        }
    )

    opt_no_throughput = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }

    markdown = _mk_markdown(items, opt_no_throughput)

    # Should NOT contain Throughput section
    assert "## Throughput" not in markdown
    assert "Throughput OK" not in markdown


def test_mk_markdown_malformed_throughput():
    """Test _mk_markdown function with malformed throughput data."""
    items = pd.DataFrame(
        {
            "est_price_mu": [25.0, 15.0],
            "est_price_sigma": [5.0, 3.0],
            "sell_p60": [0.8, 0.6],
        }
    )

    # Test with throughput as non-dict
    opt_bad_throughput = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": "invalid",  # Not a dict
    }

    markdown = _mk_markdown(items, opt_bad_throughput)

    # Should NOT contain Throughput section due to type check
    assert "## Throughput" not in markdown

    # Test with missing throughput fields
    opt_partial_throughput = {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "throughput": {
            "mins_per_unit": 5.0,
            # Missing other fields
        },
    }

    markdown = _mk_markdown(items, opt_partial_throughput)

    # Should contain Throughput section but with N/A for missing fields
    assert "## Throughput" in markdown
    assert "**Mins per unit:** 5.0" in markdown
    assert "**Capacity mins/day:** N/A" in markdown
    assert "**Total mins required (lot):** N/A" in markdown
    assert "**Available mins (horizon):** N/A" in markdown
    assert "**Throughput OK:** N/A" in markdown
