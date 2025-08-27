"""
Test cases for stress scenarios CLI.

Tests the stress_scenarios.py CLI functionality including scenario transformations,
output format validation, and basic sanity checks.
"""

import json

import pandas as pd
import pytest
from click.testing import CliRunner

from backend.cli.stress_scenarios import main as cli


def test_cli_stress_scenarios_smoke(tmp_path):
    """Test CLI basic functionality with minimal scenarios."""
    # Create synthetic test data
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-1",
                "est_price_mu": 100.0,
                "est_price_sigma": 20.0,
                "sell_p60": 0.7,
                "return_rate": 0.08,
                "shipping_per_order": 5.0,
            },
            {
                "sku_local": "TEST-2",
                "est_price_mu": 50.0,
                "est_price_sigma": 10.0,
                "sell_p60": 0.5,
                "return_rate": 0.10,
                "shipping_per_order": 3.0,
            },
        ]
    )

    in_csv = tmp_path / "test_items.csv"
    out_csv = tmp_path / "stress_results.csv"
    df.to_csv(in_csv, index=False)

    # Run CLI with baseline and one stress scenario
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--scenarios",
            "baseline,price_down_15",  # Use price_down for clearer differentiation
            "--lo",
            "10",
            "--hi",
            "200",
            "--tol",
            "5",
            "--sims",
            "100",  # Keep sims low for fast test
        ],
    )

    # Check CLI execution success
    assert res.exit_code == 0, f"CLI failed: {res.output}"

    # Verify CSV output exists and has expected structure
    assert out_csv.exists(), "Output CSV was not created"
    results_df = pd.read_csv(out_csv)

    # Should have rows for both scenarios
    assert len(results_df) == 2, f"Expected 2 scenarios, got {len(results_df)}"
    assert "baseline" in results_df["scenario"].values
    assert "price_down_15" in results_df["scenario"].values

    # Check required columns exist
    required_cols = [
        "scenario",
        "recommended_bid",
        "roi_p50",
        "prob_roi_ge_target",
        "expected_cash_60d",
        "meets_constraints",
    ]
    for col in required_cols:
        assert col in results_df.columns, f"Missing required column: {col}"

    # Basic sanity check: price_down_15 should show lower recommended bid
    baseline_row = results_df[results_df["scenario"] == "baseline"].iloc[0]
    stress_row = results_df[results_df["scenario"] == "price_down_15"].iloc[0]

    # Price down should result in lower recommended bid
    assert (
        stress_row["recommended_bid"] < baseline_row["recommended_bid"]
    ), f"price_down_15 should have lower bid than baseline: {stress_row['recommended_bid']} vs {baseline_row['recommended_bid']}"


def test_cli_stress_scenarios_json_output(tmp_path):
    """Test JSON output functionality."""
    # Minimal test data
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-JSON",
                "est_price_mu": 75.0,
                "est_price_sigma": 15.0,
                "sell_p60": 0.6,
            }
        ]
    )

    in_csv = tmp_path / "test_items.csv"
    out_csv = tmp_path / "stress_results.csv"
    out_json = tmp_path / "stress_results.json"
    df.to_csv(in_csv, index=False)

    # Run with JSON output
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--out-json",
            str(out_json),
            "--scenarios",
            "baseline,price_down_15",
            "--sims",
            "50",  # Fast test
        ],
    )

    assert res.exit_code == 0, f"CLI failed: {res.output}"

    # Verify both outputs exist
    assert out_csv.exists(), "CSV output missing"
    assert out_json.exists(), "JSON output missing"

    # Load and validate JSON structure
    with open(out_json) as f:
        json_data = json.load(f)

    assert isinstance(json_data, list), "JSON should be a list of scenarios"
    assert len(json_data) == 2, "Should have 2 scenarios"

    # Check JSON structure matches CSV
    csv_data = pd.read_csv(out_csv)
    assert len(json_data) == len(
        csv_data
    ), "JSON and CSV should have same number of rows"

    for item in json_data:
        assert "scenario" in item
        assert "recommended_bid" in item
        assert item["scenario"] in ["baseline", "price_down_15"]


def test_cli_stress_scenarios_default_scenarios(tmp_path):
    """Test running with default scenario set."""
    # Minimal test data
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-DEFAULT",
                "est_price_mu": 80.0,
                "est_price_sigma": 16.0,
                "sell_p60": 0.65,
            }
        ]
    )

    in_csv = tmp_path / "test_items.csv"
    out_csv = tmp_path / "stress_results.csv"
    df.to_csv(in_csv, index=False)

    # Run with default scenarios
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--scenarios",
            "default",
            "--sims",
            "50",  # Fast test
        ],
    )

    assert res.exit_code == 0, f"CLI failed: {res.output}"

    # Should have all 5 default scenarios
    results_df = pd.read_csv(out_csv)
    expected_scenarios = [
        "baseline",
        "price_down_15",
        "returns_up_30",
        "shipping_up_20",
        "sell_p60_down_10",
    ]
    assert len(results_df) == 5, f"Expected 5 scenarios, got {len(results_df)}"

    for scenario in expected_scenarios:
        assert (
            scenario in results_df["scenario"].values
        ), f"Missing default scenario: {scenario}"


def test_cli_stress_scenarios_invalid_scenario(tmp_path):
    """Test error handling for invalid scenario names."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "TEST-ERROR",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )

    in_csv = tmp_path / "test_items.csv"
    out_csv = tmp_path / "stress_results.csv"
    df.to_csv(in_csv, index=False)

    # Try invalid scenario name
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--scenarios",
            "invalid_scenario_name",
        ],
    )

    # Should fail with error
    assert res.exit_code != 0, "Should fail with invalid scenario name"
    assert "Unknown scenario" in res.output


def test_scenario_transformations():
    """Test individual scenario transformation functions."""
    from backend.cli.stress_scenarios import (
        apply_scenario_baseline,
        apply_scenario_price_down_15,
        apply_scenario_returns_up_30,
        apply_scenario_sell_p60_down_10,
        apply_scenario_shipping_up_20,
    )

    # Test data
    df = pd.DataFrame(
        [
            {
                "est_price_mu": 100.0,
                "est_price_sigma": 20.0,
                "est_price_p25": 85.0,
                "sell_p60": 0.8,
                "return_rate": 0.10,
                "shipping_per_order": 5.0,
            }
        ]
    )

    # Test baseline (no changes)
    baseline = apply_scenario_baseline(df)
    pd.testing.assert_frame_equal(baseline, df)

    # Test price down 15%
    price_down = apply_scenario_price_down_15(df)
    assert price_down["est_price_mu"].iloc[0] == pytest.approx(85.0)  # 100 * 0.85
    assert price_down["est_price_sigma"].iloc[0] == pytest.approx(17.0)  # 20 * 0.85
    assert price_down["est_price_p25"].iloc[0] == pytest.approx(72.25)  # 85 * 0.85

    # Test returns up 30%
    returns_up = apply_scenario_returns_up_30(df)
    assert returns_up["return_rate"].iloc[0] == pytest.approx(0.13)  # 0.10 * 1.30

    # Test shipping up 20%
    shipping_up = apply_scenario_shipping_up_20(df)
    assert shipping_up["shipping_per_order"].iloc[0] == pytest.approx(6.0)  # 5.0 * 1.20

    # Test sell_p60 down 10%
    sell_down = apply_scenario_sell_p60_down_10(df)
    assert sell_down["sell_p60"].iloc[0] == pytest.approx(0.72)  # 0.8 * 0.90

    # Test clipping behavior
    df_edge = pd.DataFrame([{"sell_p60": 0.05}])  # Will become 0.045, should stay >= 0
    sell_down_edge = apply_scenario_sell_p60_down_10(df_edge)
    assert sell_down_edge["sell_p60"].iloc[0] >= 0.0
    assert sell_down_edge["sell_p60"].iloc[0] <= 1.0
