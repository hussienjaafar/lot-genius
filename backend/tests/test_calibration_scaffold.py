"""
Tests for calibration scaffold functionality.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from lotgenius.calibration import (
    compute_metrics,
    join_predictions_outcomes,
    load_outcomes,
    load_predictions,
    log_predictions,
    suggest_adjustments,
    write_suggestions,
)


@pytest.fixture
def sample_predictions_df():
    """Sample predictions DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "sku_local": "SKU001",
                "asin": "B001TEST",
                "est_price_mu": 45.0,
                "est_price_sigma": 9.0,
                "est_price_p50": 44.5,
                "sell_p60": 0.75,
                "sell_hazard_daily": 0.02,
                "condition_bucket": "used_good",
                "sell_condition_factor": 0.85,
                "sell_seasonality_factor": 1.1,
                "quantity": 1,
            },
            {
                "sku_local": "SKU002",
                "asin": "B002TEST",
                "est_price_mu": 12.5,
                "est_price_sigma": 2.5,
                "est_price_p50": 12.0,
                "sell_p60": 0.60,
                "sell_hazard_daily": 0.015,
                "condition_bucket": "new",
                "sell_condition_factor": 1.0,
                "sell_seasonality_factor": 0.95,
                "quantity": 2,
            },
            {
                "sku_local": "SKU003",
                "est_price_mu": 89.0,
                "est_price_sigma": 18.0,
                "est_price_p50": 87.5,
                "sell_p60": 0.45,
                "sell_hazard_daily": 0.01,
                "condition_bucket": "like_new",
                "sell_condition_factor": 0.95,
                "sell_seasonality_factor": 1.2,
                "quantity": 1,
            },
            {
                "sku_local": "SKU004",
                "asin": "B004TEST",
                "est_price_mu": 25.0,
                "est_price_sigma": 5.0,
                "est_price_p50": 24.0,
                "sell_p60": 0.80,
                "sell_hazard_daily": 0.03,
                "condition_bucket": "used_good",  # Second item with used_good condition
                "sell_condition_factor": 0.85,
                "sell_seasonality_factor": 1.0,
                "quantity": 1,
            },
        ]
    )


@pytest.fixture
def sample_outcomes_df():
    """Sample outcomes DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "sku_local": "SKU001",
                "realized_price": 42.0,
                "sold_within_horizon": True,
                "days_to_sale": 28,
            },
            {
                "sku_local": "SKU002",
                "realized_price": 15.0,
                "sold_within_horizon": True,
                "days_to_sale": 45,
            },
            {
                "sku_local": "SKU003",
                "realized_price": 65.0,  # Give valid price for testing
                "sold_within_horizon": True,
                "days_to_sale": 35,
            },
            {
                "sku_local": "SKU004",
                "realized_price": 28.0,
                "sold_within_horizon": True,
                "days_to_sale": 18,
            },
        ]
    )


def test_log_predictions(sample_predictions_df):
    """Test prediction logging to JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "predictions.jsonl"
        context = {
            "roi_target": 1.25,
            "risk_threshold": 0.80,
            "horizon_days": 60,
            "lot_id": "TEST_LOT_001",
        }

        count = log_predictions(sample_predictions_df, context, str(output_path))

        assert count == 4
        assert output_path.exists()

        # Verify JSONL content
        records = []
        with open(output_path, "r") as f:
            for line in f:
                records.append(json.loads(line))

        assert len(records) == 4
        assert records[0]["sku_local"] == "SKU001"
        assert records[0]["est_price_mu"] == 45.0
        assert records[0]["sell_p60"] == 0.75
        assert records[0]["lot_id"] == "TEST_LOT_001"
        assert records[0]["horizon_days"] == 60


def test_log_predictions_empty_df():
    """Test logging with empty DataFrame."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "empty.jsonl"
        context = {"roi_target": 1.25}

        count = log_predictions(pd.DataFrame(), context, str(output_path))

        assert count == 0
        assert not output_path.exists()


def test_load_predictions(sample_predictions_df):
    """Test loading predictions from JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "predictions.jsonl"
        context = {"roi_target": 1.25, "horizon_days": 60}

        # First log some predictions
        log_predictions(sample_predictions_df, context, str(jsonl_path))

        # Then load them back
        loaded_df = load_predictions(str(jsonl_path))

        assert len(loaded_df) == 4
        assert "sku_local" in loaded_df.columns
        assert "est_price_mu" in loaded_df.columns
        assert "sell_p60" in loaded_df.columns


def test_load_outcomes(sample_outcomes_df):
    """Test loading outcomes from CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "outcomes.csv"
        sample_outcomes_df.to_csv(csv_path, index=False)

        loaded_df = load_outcomes(str(csv_path))

        assert len(loaded_df) == 4
        assert "sku_local" in loaded_df.columns
        assert "realized_price" in loaded_df.columns
        assert "sold_within_horizon" in loaded_df.columns
        assert loaded_df["sold_within_horizon"].dtype == bool


def test_load_outcomes_column_variations():
    """Test loading outcomes with various column name variations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "outcomes_alt.csv"

        # Use alternative column names
        alt_df = pd.DataFrame(
            [
                {
                    "SKU": "SKU001",
                    "Sale_Price": 42.0,
                    "Sold": 1,
                    "Days_Held": 28,
                }
            ]
        )
        alt_df.to_csv(csv_path, index=False)

        loaded_df = load_outcomes(str(csv_path))

        assert len(loaded_df) == 1
        assert "sku_local" in loaded_df.columns
        assert "realized_price" in loaded_df.columns
        assert "sold_within_horizon" in loaded_df.columns
        assert "days_to_sale" in loaded_df.columns


def test_join_predictions_outcomes(sample_predictions_df, sample_outcomes_df):
    """Test joining predictions with outcomes."""
    joined_df = join_predictions_outcomes(sample_predictions_df, sample_outcomes_df)

    assert len(joined_df) == 4  # All should match on sku_local
    assert "est_price_mu" in joined_df.columns
    assert "realized_price" in joined_df.columns
    assert "sold_within_horizon" in joined_df.columns


def test_compute_metrics(sample_predictions_df, sample_outcomes_df):
    """Test metrics computation."""
    joined_df = join_predictions_outcomes(sample_predictions_df, sample_outcomes_df)
    metrics = compute_metrics(joined_df, horizon_days=60)

    # Check structure
    assert "n_samples" in metrics
    assert "horizon_days" in metrics
    assert metrics["horizon_days"] == 60

    # Check price metrics (should be present for matching records)
    assert "price_metrics" in metrics
    price_metrics = metrics["price_metrics"]
    assert "mae" in price_metrics
    assert "rmse" in price_metrics
    assert "mape" in price_metrics
    assert "n_samples" in price_metrics

    # Validate metrics are reasonable
    assert price_metrics["mae"] >= 0
    assert price_metrics["rmse"] >= 0
    assert price_metrics["n_samples"] == 4  # All SKUs have realized prices now

    # Check probability metrics
    assert "probability_metrics" in metrics
    prob_metrics = metrics["probability_metrics"]
    assert "brier_score" in prob_metrics
    assert "calibration_bins" in prob_metrics
    assert prob_metrics["brier_score"] >= 0
    assert prob_metrics["brier_score"] <= 1


def test_suggest_adjustments(sample_predictions_df, sample_outcomes_df):
    """Test adjustment suggestions."""
    joined_df = join_predictions_outcomes(sample_predictions_df, sample_outcomes_df)
    suggestions = suggest_adjustments(joined_df)

    # Check structure
    assert "timestamp" in suggestions
    assert "n_samples" in suggestions

    # Should have condition price factor suggestions
    assert "condition_price_factors" in suggestions
    condition_adjustments = suggestions["condition_price_factors"]

    # Check that we have reasonable suggestions
    for condition, adj in condition_adjustments.items():
        assert "current_factor" in adj
        assert "median_ratio" in adj
        assert "suggested_factor" in adj
        assert "n_samples" in adj

        # Suggested factor should be bounded
        assert 0.3 <= adj["suggested_factor"] <= 1.5
        assert adj["n_samples"] >= 1


def test_write_suggestions():
    """Test writing suggestions to JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        suggestions_path = Path(tmpdir) / "suggestions.json"

        test_suggestions = {
            "timestamp": "2024-01-01T12:00:00Z",
            "n_samples": 10,
            "condition_price_factors": {
                "new": {"current_factor": 1.0, "suggested_factor": 1.05, "n_samples": 5}
            },
        }

        write_suggestions(test_suggestions, str(suggestions_path))

        assert suggestions_path.exists()

        # Verify content
        with open(suggestions_path, "r") as f:
            loaded = json.load(f)

        assert loaded["n_samples"] == 10
        assert "condition_price_factors" in loaded


def test_compute_metrics_edge_cases():
    """Test metrics computation with edge cases."""
    # Empty DataFrame
    empty_metrics = compute_metrics(pd.DataFrame(), 60)
    assert empty_metrics["n_samples"] == 0

    # DataFrame with missing critical columns
    partial_df = pd.DataFrame([{"sku_local": "SKU001"}])
    partial_metrics = compute_metrics(partial_df, 60)
    assert partial_metrics["n_samples"] == 1
    # Should not have price or probability metrics
    assert "price_metrics" not in partial_metrics
    assert "probability_metrics" not in partial_metrics


def test_brier_score_perfect_calibration():
    """Test Brier score calculation with perfect calibration."""
    # Create perfectly calibrated predictions
    perfect_df = pd.DataFrame(
        [
            {"sell_p60": 0.0, "sold_within_horizon": False},
            {"sell_p60": 0.5, "sold_within_horizon": False},
            {"sell_p60": 0.5, "sold_within_horizon": True},
            {"sell_p60": 1.0, "sold_within_horizon": True},
        ]
    )

    metrics = compute_metrics(perfect_df, 60)

    # Perfect calibration should have low Brier score
    assert "probability_metrics" in metrics
    brier = metrics["probability_metrics"]["brier_score"]
    assert 0 <= brier <= 0.5  # Should be quite good for this small sample


def test_condition_adjustments_bounds():
    """Test that condition adjustment suggestions are properly bounded."""
    # Create data that would suggest extreme adjustments
    extreme_df = pd.DataFrame(
        [
            {
                "condition_bucket": "test_condition",
                "est_price_mu": 10.0,
                "realized_price": 100.0,  # 10x higher than predicted
            },
            {
                "condition_bucket": "test_condition",
                "est_price_mu": 20.0,
                "realized_price": 200.0,  # 10x higher than predicted
            },
        ]
    )

    suggestions = suggest_adjustments(extreme_df)

    if "condition_price_factors" in suggestions:
        for condition, adj in suggestions["condition_price_factors"].items():
            # Should be bounded to reasonable range
            assert 0.3 <= adj["suggested_factor"] <= 1.5


def test_log_predictions_append_behavior(sample_predictions_df):
    """Test that log_predictions appends to existing files instead of overwriting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "predictions.jsonl"
        context = {
            "roi_target": 1.25,
            "risk_threshold": 0.80,
            "horizon_days": 60,
            "lot_id": "TEST_LOT_001",
        }

        # First call - log predictions
        count1 = log_predictions(sample_predictions_df, context, str(output_path))
        assert count1 == 4
        assert output_path.exists()

        # Count lines after first call
        with open(output_path, "r") as f:
            lines1 = f.readlines()
        assert len(lines1) == 4

        # Second call - should append, not overwrite
        count2 = log_predictions(sample_predictions_df, context, str(output_path))
        assert count2 == 4

        # Count lines after second call - should be doubled
        with open(output_path, "r") as f:
            lines2 = f.readlines()
        assert len(lines2) == 8  # First 4 + second 4

        # Verify both sets of records are present
        records = []
        for line in lines2:
            if line.strip():
                records.append(json.loads(line))

        assert len(records) == 8
        # Should have two records for each SKU
        sku_counts = {}
        for record in records:
            sku = record.get("sku_local")
            sku_counts[sku] = sku_counts.get(sku, 0) + 1

        # Each SKU should appear exactly twice
        for sku, count in sku_counts.items():
            assert count == 2, f"SKU {sku} should appear 2 times, got {count}"


def test_log_predictions_nested_context(sample_predictions_df):
    """Test that log_predictions includes nested context object alongside flattened keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "predictions.jsonl"
        context = {
            "roi_target": 1.25,
            "risk_threshold": 0.80,
            "horizon_days": 60,
            "lot_id": "TEST_LOT_002",
            "opt_source": "run_optimize",
            "opt_params": {"roi_target": 1.25, "risk_threshold": 0.80, "sims": 100},
        }

        count = log_predictions(sample_predictions_df, context, str(output_path))
        assert count == 4

        # Load first record and verify structure
        with open(output_path, "r") as f:
            first_line = f.readline().strip()

        record = json.loads(first_line)

        # Verify nested context object exists
        assert "context" in record
        assert isinstance(record["context"], dict)

        # Verify nested context contains expected keys
        ctx = record["context"]
        assert "roi_target" in ctx
        assert "risk_threshold" in ctx
        assert "opt_source" in ctx
        assert "opt_params" in ctx
        assert "timestamp" in ctx

        # Verify nested context values match input
        assert ctx["roi_target"] == 1.25
        assert ctx["risk_threshold"] == 0.80
        assert ctx["opt_source"] == "run_optimize"
        assert ctx["opt_params"]["sims"] == 100

        # Verify flattened keys are still present for back-compat
        assert "roi_target" in record
        assert "risk_threshold" in record
        assert "horizon_days" in record
        assert "lot_id" in record
        assert "timestamp" in record

        # Verify aliases are present
        assert "predicted_price" in record
        assert "predicted_sell_p60" in record

        # Verify aliases match original values
        assert record["predicted_price"] == record["est_price_mu"]
        assert record["predicted_sell_p60"] == record["sell_p60"]
