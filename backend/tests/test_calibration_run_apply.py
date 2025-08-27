"""Tests for calibration run and apply CLIs."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from cli.calibration_apply import main as calibration_apply_main
from cli.calibration_run import main as calibration_run_main
from click.testing import CliRunner


class TestCalibrationRunApply:
    """Test calibration run and apply CLI functionality."""

    def create_test_data(self, tmp_dir):
        """Create minimal test data for calibration testing."""
        # Create predictions JSONL
        predictions_path = Path(tmp_dir) / "predictions.jsonl"
        predictions = [
            {
                "sku_local": "item1",
                "predicted_sell_p60": 0.8,
                "predicted_price": 100.0,
                "condition": "new",
                "category": "electronics",
            },
            {
                "sku_local": "item2",
                "predicted_sell_p60": 0.6,
                "predicted_price": 80.0,
                "condition": "used_good",
                "category": "electronics",
            },
            {
                "sku_local": "item3",
                "predicted_sell_p60": 0.7,
                "predicted_price": 120.0,
                "condition": "like_new",
                "category": "books",
            },
        ]

        with open(predictions_path, "w") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")

        # Create outcomes CSV
        outcomes_path = Path(tmp_dir) / "outcomes.csv"
        outcomes_data = pd.DataFrame(
            [
                {
                    "sku_local": "item1",
                    "actual_sell_p60": 0.85,
                    "actual_price": 105.0,
                    "sold": True,
                },
                {
                    "sku_local": "item2",
                    "actual_sell_p60": 0.55,
                    "actual_price": 75.0,
                    "sold": True,
                },
                {
                    "sku_local": "item3",
                    "actual_sell_p60": 0.75,
                    "actual_price": 115.0,
                    "sold": True,
                },
            ]
        )
        outcomes_data.to_csv(outcomes_path, index=False)

        return predictions_path, outcomes_path

    @patch("lotgenius.calibration.load_predictions")
    @patch("lotgenius.calibration.load_outcomes")
    @patch("lotgenius.calibration.join_predictions_outcomes")
    @patch("lotgenius.calibration.compute_metrics")
    @patch("lotgenius.calibration.suggest_adjustments")
    @patch("lotgenius.calibration.write_suggestions")
    def test_calibration_run_basic(
        self,
        mock_write_suggestions,
        mock_suggest_adjustments,
        mock_compute_metrics,
        mock_join_predictions_outcomes,
        mock_load_outcomes,
        mock_load_predictions,
    ):
        """Test basic calibration run functionality."""
        # Mock the calibration functions
        mock_load_predictions.return_value = [
            {"sku_local": "item1", "predicted_sell_p60": 0.8}
        ]
        mock_load_outcomes.return_value = [
            {"sku_local": "item1", "actual_sell_p60": 0.85}
        ]
        mock_join_predictions_outcomes.return_value = [
            {
                "sku_local": "item1",
                "predicted_sell_p60": 0.8,
                "actual_sell_p60": 0.85,
                "condition": "new",
            }
        ]
        mock_compute_metrics.return_value = {
            "overall": {"mae": 0.05, "rmse": 0.05, "bias": -0.05}
        }
        mock_suggest_adjustments.return_value = {
            "suggestions": [
                {
                    "type": "condition_price_factor",
                    "condition": "new",
                    "suggested_factor": 0.98,
                }
            ]
        }

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            predictions_path, outcomes_path = self.create_test_data(tmp_dir)
            metrics_path = Path(tmp_dir) / "metrics.json"
            suggestions_path = Path(tmp_dir) / "suggestions.json"

            result = runner.invoke(
                calibration_run_main,
                [
                    str(predictions_path),
                    str(outcomes_path),
                    "--out-metrics",
                    str(metrics_path),
                    "--out-suggestions",
                    str(suggestions_path),
                    "--history-dir",
                    str(Path(tmp_dir) / "history"),
                ],
            )

            assert result.exit_code == 0
            assert "Calibration Run Complete" in result.output
            assert mock_load_predictions.called
            assert mock_load_outcomes.called
            assert mock_compute_metrics.called
            assert mock_suggest_adjustments.called

    def test_calibration_apply_basic(self):
        """Test basic calibration apply functionality."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create suggestions file
            suggestions_path = Path(tmp_dir) / "suggestions.json"
            suggestions_data = {
                "suggestions": [
                    {
                        "type": "condition_price_factor",
                        "condition": "new",
                        "suggested_factor": 0.98,
                    },
                    {
                        "type": "condition_price_factor",
                        "condition": "used_good",
                        "suggested_factor": 0.82,
                    },
                    {"type": "other_suggestion", "data": "should be ignored"},
                ]
            }

            with open(suggestions_path, "w") as f:
                json.dump(suggestions_data, f)

            overrides_path = Path(tmp_dir) / "overrides.json"

            result = runner.invoke(
                calibration_apply_main,
                [
                    "--suggestions",
                    str(suggestions_path),
                    "--out-overrides",
                    str(overrides_path),
                ],
            )

            assert result.exit_code == 0
            assert overrides_path.exists()

            # Check overrides content
            with open(overrides_path, "r") as f:
                overrides = json.load(f)

            assert "CONDITION_PRICE_FACTOR" in overrides
            factors = overrides["CONDITION_PRICE_FACTOR"]
            assert factors["new"] == 0.98
            assert factors["used_good"] == 0.82
            assert len(factors) == 2  # Only condition price factors

    def test_calibration_apply_bounds(self):
        """Test that calibration apply correctly applies bounds."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create suggestions with values outside bounds
            suggestions_path = Path(tmp_dir) / "suggestions.json"
            suggestions_data = {
                "suggestions": [
                    {
                        "type": "condition_price_factor",
                        "condition": "new",
                        "suggested_factor": 1.5,  # Above default max of 1.2
                    },
                    {
                        "type": "condition_price_factor",
                        "condition": "used_good",
                        "suggested_factor": 0.3,  # Below default min of 0.5
                    },
                    {
                        "type": "condition_price_factor",
                        "condition": "like_new",
                        "suggested_factor": 0.9,  # Within bounds
                    },
                ]
            }

            with open(suggestions_path, "w") as f:
                json.dump(suggestions_data, f)

            overrides_path = Path(tmp_dir) / "overrides.json"

            result = runner.invoke(
                calibration_apply_main,
                [
                    "--suggestions",
                    str(suggestions_path),
                    "--out-overrides",
                    str(overrides_path),
                    "--min-factor",
                    "0.5",
                    "--max-factor",
                    "1.2",
                ],
            )

            assert result.exit_code == 0
            assert "Bounded" in result.output  # Should show bounded adjustments

            # Check bounded values
            with open(overrides_path, "r") as f:
                overrides = json.load(f)

            factors = overrides["CONDITION_PRICE_FACTOR"]
            assert factors["new"] == 1.2  # Clamped to max
            assert factors["used_good"] == 0.5  # Clamped to min
            assert factors["like_new"] == 0.9  # Unchanged (within bounds)

    def test_calibration_apply_dry_run(self):
        """Test dry run functionality."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            suggestions_path = Path(tmp_dir) / "suggestions.json"
            suggestions_data = {
                "suggestions": [
                    {
                        "type": "condition_price_factor",
                        "condition": "new",
                        "suggested_factor": 0.95,
                    }
                ]
            }

            with open(suggestions_path, "w") as f:
                json.dump(suggestions_data, f)

            overrides_path = Path(tmp_dir) / "overrides.json"

            result = runner.invoke(
                calibration_apply_main,
                [
                    "--suggestions",
                    str(suggestions_path),
                    "--out-overrides",
                    str(overrides_path),
                    "--dry-run",
                ],
            )

            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Would write to:" in result.output
            # File should not be created in dry run
            assert not overrides_path.exists()

    def test_calibration_apply_no_suggestions(self):
        """Test behavior when no condition factor suggestions are found."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            suggestions_path = Path(tmp_dir) / "suggestions.json"
            suggestions_data = {
                "suggestions": [
                    {"type": "other_type", "data": "not a condition factor suggestion"}
                ]
            }

            with open(suggestions_path, "w") as f:
                json.dump(suggestions_data, f)

            overrides_path = Path(tmp_dir) / "overrides.json"

            result = runner.invoke(
                calibration_apply_main,
                [
                    "--suggestions",
                    str(suggestions_path),
                    "--out-overrides",
                    str(overrides_path),
                ],
            )

            assert result.exit_code == 0
            assert "No condition price factor suggestions found" in result.output
            assert overrides_path.exists()

            # Should create empty overrides
            with open(overrides_path, "r") as f:
                overrides = json.load(f)

            assert overrides == {"CONDITION_PRICE_FACTOR": {}}
