"""Test CLI report generation with stress scenario data."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner
from lotgenius.cli.report_lot import main


@pytest.fixture
def sample_items_csv():
    """Create a minimal items CSV for testing."""
    data = {
        "asin": ["B001", "B002"],
        "est_price_mu": [25.0, 15.0],
        "est_price_p50": [24.0, 14.0],
        "sell_p60": [0.8, 0.6],
        "quantity": [1, 2],
    }
    df = pd.DataFrame(data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        return Path(f.name)


@pytest.fixture
def sample_opt_json():
    """Create a minimal optimizer JSON for testing."""
    data = {
        "bid": 30.0,
        "roi_p50": 1.5,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 35.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return Path(f.name)


@pytest.fixture
def sample_stress_csv():
    """Create a stress scenarios CSV for testing."""
    data = [
        {
            "scenario": "baseline",
            "bid": 30.0,
            "prob_roi_ge_target": 0.85,
            "expected_cash_60d": 35.0,
        },
        {
            "scenario": "price_down_15",
            "bid": 25.5,
            "prob_roi_ge_target": 0.72,
            "expected_cash_60d": 29.8,
        },
        {
            "scenario": "returns_up_30",
            "bid": 28.0,
            "prob_roi_ge_target": 0.78,
            "expected_cash_60d": 32.1,
        },
    ]
    df = pd.DataFrame(data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        return Path(f.name)


@pytest.fixture
def sample_stress_json():
    """Create a stress scenarios JSON for testing."""
    data = [
        {
            "scenario": "baseline",
            "bid": 30.0,
            "prob_roi_ge_target": 0.85,
            "expected_cash_60d": 35.0,
        },
        {
            "scenario": "sell_p60_down_10",
            "bid": 27.5,
            "prob_roi_ge_target": 0.76,
            "expected_cash_60d": 31.2,
        },
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return Path(f.name)


def test_report_basic_no_stress(sample_items_csv, sample_opt_json):
    """Test basic report generation without stress data."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
            ],
        )

        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "Executive Summary" in content
        assert "$30.00" in content  # bid
        assert "1.50×" in content  # roi_p50
        assert "85.0%" in content  # prob_roi_ge_target
        assert "Scenario Diffs" not in content  # No stress data

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_report_with_stress_csv(sample_items_csv, sample_opt_json, sample_stress_csv):
    """Test report generation with stress CSV data."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
                "--stress-csv",
                str(sample_stress_csv),
            ],
        )

        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "## Scenario Diffs" in content

        # Check table structure
        assert (
            "| Scenario | Bid | Δ Bid | Prob ≥ Target | Δ Prob | 60d Cash | Δ Cash |"
            in content
        )
        assert "| **baseline**" in content
        assert "| **price_down_15**" in content
        assert "| **returns_up_30**" in content

        # Check deltas (price_down_15 should show negative deltas)
        assert "-$4.50" in content  # bid delta
        assert "-13.0%" in content  # prob delta
        assert "-$5.20" in content  # cash delta

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        sample_stress_csv.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_report_with_stress_json(sample_items_csv, sample_opt_json, sample_stress_json):
    """Test report generation with stress JSON data."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
                "--stress-json",
                str(sample_stress_json),
            ],
        )

        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "## Scenario Diffs" in content

        # Check table structure
        assert "| **baseline**" in content
        assert "| **sell_p60_down_10**" in content

        # Check deltas (sell_p60_down_10 should show negative deltas)
        assert "-$2.50" in content  # bid delta
        assert "-9.0%" in content  # prob delta
        assert "-$3.80" in content  # cash delta

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        sample_stress_json.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_report_with_invalid_stress_csv(sample_items_csv, sample_opt_json):
    """Test report generation with invalid stress CSV (missing columns)."""
    # Create invalid stress CSV (missing required columns)
    invalid_data = {"scenario": ["baseline"], "bad_column": [1.0]}
    df = pd.DataFrame(invalid_data)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        invalid_stress_csv = Path(f.name)

    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
                "--stress-csv",
                str(invalid_stress_csv),
            ],
        )

        # Should succeed but ignore invalid stress data
        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "Scenario Diffs" not in content  # Invalid data should be ignored

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        invalid_stress_csv.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_report_with_missing_baseline_stress(sample_items_csv, sample_opt_json):
    """Test report generation when stress data has no baseline scenario."""
    # Create stress CSV without baseline
    data = [
        {
            "scenario": "price_down_15",
            "bid": 25.5,
            "prob_roi_ge_target": 0.72,
            "expected_cash_60d": 29.8,
        }
    ]
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        no_baseline_csv = Path(f.name)

    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
                "--stress-csv",
                str(no_baseline_csv),
            ],
        )

        # Should succeed but not show Scenario Diffs without baseline
        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "Scenario Diffs" not in content  # No baseline = no table

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        no_baseline_csv.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_report_stress_csv_precedence(
    sample_items_csv, sample_opt_json, sample_stress_csv, sample_stress_json
):
    """Test that stress CSV takes precedence over stress JSON when both are provided."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        out_md = Path(f.name)

    try:
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(sample_items_csv),
                "--opt-json",
                str(sample_opt_json),
                "--out-markdown",
                str(out_md),
                "--stress-csv",
                str(sample_stress_csv),
                "--stress-json",
                str(sample_stress_json),
            ],
        )

        assert result.exit_code == 0
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "# Lot Genius Report" in content
        assert "## Scenario Diffs" in content

        # Should contain CSV scenarios, not JSON scenarios
        assert "price_down_15" in content  # From CSV
        assert "returns_up_30" in content  # From CSV
        assert "sell_p60_down_10" not in content  # From JSON, should be ignored

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
        sample_opt_json.unlink(missing_ok=True)
        sample_stress_csv.unlink(missing_ok=True)
        sample_stress_json.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)
