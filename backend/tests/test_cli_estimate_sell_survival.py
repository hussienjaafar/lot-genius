"""Tests for CLI estimate_sell with survival model."""

import tempfile
from pathlib import Path

import pandas as pd
from cli.estimate_sell import main
from click.testing import CliRunner


class TestCLIEstimateSellSurvival:
    """Test CLI estimate_sell functionality with survival model."""

    def test_cli_default_uses_survival_model(self):
        """Test that CLI uses survival model by default."""
        runner = CliRunner()

        # Create test input CSV
        test_data = pd.DataFrame(
            [
                {
                    "title": "Test Item",
                    "condition": "New",
                    "category": "electronics",
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test_input.csv"
            output_file = Path(tmp_dir) / "test_output.csv"

            test_data.to_csv(input_file, index=False)

            # Run CLI without specifying survival model (should use default)
            result = runner.invoke(main, [str(input_file), str(output_file)])

            assert result.exit_code == 0
            assert output_file.exists()

            # Check output has survival model columns
            output_df = pd.read_csv(output_file)
            survival_columns = [
                "sell_p60",
                "sell_alpha_used",
                "sell_beta_used",
                "sell_alpha_scale_category",
            ]
            for col in survival_columns:
                assert col in output_df.columns

    def test_cli_survival_model_override(self):
        """Test that CLI respects --survival-model override."""
        runner = CliRunner()

        test_data = pd.DataFrame(
            [
                {
                    "title": "Test Item",
                    "condition": "New",
                    "category": "electronics",
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                    "keepa_price_new_med": 95.0,
                    "keepa_offers_count": 10,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test_input.csv"
            output_file = Path(tmp_dir) / "test_output.csv"

            test_data.to_csv(input_file, index=False)

            # Run CLI with explicit proxy model
            result = runner.invoke(
                main, [str(input_file), str(output_file), "--survival-model", "proxy"]
            )

            assert result.exit_code == 0
            assert output_file.exists()

            # Check output has proxy model columns (not survival-specific ones)
            output_df = pd.read_csv(output_file)
            assert "sell_p60" in output_df.columns
            # These columns should NOT be present with proxy model
            assert "sell_alpha_used" not in output_df.columns
            assert "sell_beta_used" not in output_df.columns

    def test_cli_survival_fields_reasonable_ranges(self):
        """Test that survival model produces reasonable field values."""
        runner = CliRunner()

        test_data = pd.DataFrame(
            [
                {
                    "title": "Test Item",
                    "condition": "New",
                    "category": "electronics",
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test_input.csv"
            output_file = Path(tmp_dir) / "test_output.csv"

            test_data.to_csv(input_file, index=False)

            result = runner.invoke(
                main,
                [str(input_file), str(output_file), "--survival-model", "loglogistic"],
            )

            assert result.exit_code == 0
            output_df = pd.read_csv(output_file)

            # Check reasonable ranges
            row = output_df.iloc[0]

            # Probability should be between 0 and 1
            assert 0.0 <= row["sell_p60"] <= 1.0

            # Hazard should be positive
            assert row["sell_hazard_daily"] > 0

            # Alpha and beta should be positive
            assert row["sell_alpha_used"] > 0
            assert row["sell_beta_used"] > 0

            # Alpha scale should be positive
            assert row["sell_alpha_scale_category"] > 0

            # PTM z-score should be reasonable
            assert -10 <= row["sell_ptm_z"] <= 10
