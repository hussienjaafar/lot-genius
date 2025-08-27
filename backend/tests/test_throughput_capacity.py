"""Test throughput capacity gating and CLI integration."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner
from lotgenius.config import settings
from lotgenius.roi import feasible

from backend.cli.optimize_bid import main


@pytest.fixture
def sample_items_df():
    """Create a minimal items DataFrame for testing."""
    data = {
        "est_price_mu": [25.0, 15.0, 30.0],
        "est_price_sigma": [5.0, 3.0, 6.0],
        "sell_p60": [0.8, 0.6, 0.7],
        "quantity": [2, 3, 1],  # Total of 6 units
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_items_csv(sample_items_df):
    """Create a CSV file from the sample DataFrame."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_items_df.to_csv(f.name, index=False)
        return Path(f.name)


def test_throughput_gating_unit(sample_items_df):
    """Unit test for throughput gating in feasible function."""
    bid = 50.0

    # Test case: tight capacity that should fail throughput check
    # 6 units * 100 mins/unit = 600 mins required
    # 5 mins/day * 60 days = 300 mins available, so 600 > 300 should fail
    ok, result = feasible(
        sample_items_df,
        bid,
        throughput_mins_per_unit=100.0,  # High mins per unit
        capacity_mins_per_day=5.0,  # Very low capacity
        roi_target=1.1,  # Low target to avoid ROI constraint failure
        risk_threshold=0.1,  # Low threshold to avoid risk constraint failure
    )

    # Should fail due to throughput constraint
    assert not ok
    assert result["meets_constraints"] is False
    assert "throughput" in result
    assert result["throughput"]["throughput_ok"] is False
    assert result["throughput"]["mins_per_unit"] == 100.0
    assert result["throughput"]["capacity_mins_per_day"] == 5.0
    assert result["throughput"]["total_minutes_required"] == 600.0  # 6 units * 100 mins

    # Calculate expected available minutes
    expected_available = 5.0 * settings.SELLTHROUGH_HORIZON_DAYS
    assert result["throughput"]["available_minutes"] == expected_available


def test_throughput_gating_pass(sample_items_df):
    """Test throughput gating when capacity is sufficient."""
    bid = 50.0

    # Test case: generous capacity that should pass
    ok, result = feasible(
        sample_items_df,
        bid,
        throughput_mins_per_unit=1.0,  # Low mins per unit
        capacity_mins_per_day=1000.0,  # High capacity
        roi_target=1.1,  # Low target to avoid ROI constraint failure
        risk_threshold=0.1,  # Low threshold to avoid risk constraint failure
    )

    # Should pass throughput constraint (other constraints may still fail)
    assert "throughput" in result
    assert result["throughput"]["throughput_ok"] is True
    assert result["throughput"]["total_minutes_required"] == 6.0  # 6 units * 1 min

    expected_available = 1000.0 * settings.SELLTHROUGH_HORIZON_DAYS
    assert result["throughput"]["available_minutes"] == expected_available


def test_cli_throughput_failure(sample_items_csv, tmp_path):
    """Test CLI with throughput parameters that cause failure."""
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
                "100.0",
                "--mins-per-unit",
                "100.0",  # High mins per unit
                "--capacity-mins-per-day",
                "5.0",  # Low capacity
                "--roi-target",
                "1.1",  # Low target to isolate throughput constraint
                "--risk-threshold",
                "0.1",  # Low threshold
                "--evidence-out",
                str(evidence_out),
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()

        # Check that the optimization failed due to throughput
        result_data = json.loads(out_json.read_text(encoding="utf-8"))
        assert "meets_constraints" in result_data
        assert result_data["meets_constraints"] is False

        # Check throughput data is present
        assert "throughput" in result_data
        throughput = result_data["throughput"]
        assert throughput["throughput_ok"] is False
        assert throughput["mins_per_unit"] == 100.0
        assert throughput["capacity_mins_per_day"] == 5.0
        assert throughput["total_minutes_required"] == 600.0  # 6 units * 100 mins

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)


def test_cli_throughput_success(sample_items_csv, tmp_path):
    """Test CLI with throughput parameters that should pass."""
    runner = CliRunner()

    out_json = tmp_path / "test_optimize.json"

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
                "100.0",
                "--mins-per-unit",
                "1.0",  # Low mins per unit
                "--capacity-mins-per-day",
                "1000.0",  # High capacity
                "--roi-target",
                "1.1",  # Low target
                "--risk-threshold",
                "0.1",  # Low threshold
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()

        # Check that throughput constraint passed
        result_data = json.loads(out_json.read_text(encoding="utf-8"))
        assert "throughput" in result_data
        throughput = result_data["throughput"]
        assert throughput["throughput_ok"] is True
        assert throughput["mins_per_unit"] == 1.0
        assert throughput["capacity_mins_per_day"] == 1000.0
        assert throughput["total_minutes_required"] == 6.0  # 6 units * 1 min

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)


def test_cli_throughput_defaults(sample_items_csv, tmp_path):
    """Test CLI without throughput flags uses settings defaults."""
    runner = CliRunner()

    out_json = tmp_path / "test_optimize.json"

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
                "100.0",
                "--roi-target",
                "1.1",
                "--risk-threshold",
                "0.1",
            ],
        )

        assert result.exit_code == 0
        assert out_json.exists()

        # Check that throughput data uses settings defaults
        result_data = json.loads(out_json.read_text(encoding="utf-8"))
        assert "throughput" in result_data
        throughput = result_data["throughput"]

        # Should use settings values
        assert throughput["mins_per_unit"] == settings.THROUGHPUT_MINS_PER_UNIT
        assert (
            throughput["capacity_mins_per_day"]
            == settings.THROUGHPUT_CAPACITY_MINS_PER_DAY
        )

    finally:
        # Cleanup
        sample_items_csv.unlink(missing_ok=True)
