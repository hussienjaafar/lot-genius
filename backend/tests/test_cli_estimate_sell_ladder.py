"""Tests for CLI estimate_sell with pricing ladder integration."""

import json
import tempfile
from pathlib import Path

import pandas as pd
from cli.estimate_sell import main
from click.testing import CliRunner


class TestCLIEstimateSellLadder:
    """Test CLI estimate_sell functionality with pricing ladder."""

    def test_cli_ladder_integration_survival_model(self):
        """Test that ladder integration works with survival model."""
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

            # Run CLI with ladder enabled and survival model
            result = runner.invoke(
                main,
                [
                    str(input_file),
                    str(output_file),
                    "--survival-model",
                    "loglogistic",
                    "--use-pricing-ladder",
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

            output_df = pd.read_csv(output_file)

            # Check ladder-specific columns are present
            ladder_columns = ["sell_p60_ladder", "sell_ladder_segments"]
            for col in ladder_columns:
                assert col in output_df.columns
                assert pd.notna(output_df.iloc[0][col])

            # Check that sell_p60 was updated with ladder version
            assert output_df.iloc[0]["sell_p60"] == output_df.iloc[0]["sell_p60_ladder"]

            # Check ladder segments are valid JSON
            segments_json = output_df.iloc[0]["sell_ladder_segments"]
            segments = json.loads(segments_json)
            assert isinstance(segments, list)
            assert len(segments) > 0

            # Each segment should have required fields
            for segment in segments:
                assert "price" in segment
                assert "hazard_multiplier" in segment
                assert "days" in segment
                assert segment["price"] > 0
                assert segment["hazard_multiplier"] > 0
                assert segment["days"] > 0

    def test_cli_ladder_integration_proxy_model(self):
        """Test that ladder integration works with proxy model too."""
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

            # Run CLI with ladder enabled and proxy model
            result = runner.invoke(
                main,
                [
                    str(input_file),
                    str(output_file),
                    "--survival-model",
                    "proxy",
                    "--use-pricing-ladder",
                ],
            )

            assert result.exit_code == 0
            output_df = pd.read_csv(output_file)

            # Check ladder columns are present regardless of base model
            assert "sell_p60_ladder" in output_df.columns
            assert "sell_ladder_segments" in output_df.columns
            assert pd.notna(output_df.iloc[0]["sell_p60_ladder"])

    def test_cli_no_ladder_preserves_base_model(self):
        """Test that without ladder, base model results are preserved."""
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

            # Run CLI without ladder
            result = runner.invoke(
                main,
                [
                    str(input_file),
                    str(output_file),
                    "--survival-model",
                    "loglogistic",
                    "--no-pricing-ladder",  # Explicitly disable ladder
                ],
            )

            assert result.exit_code == 0
            output_df = pd.read_csv(output_file)

            # Check base model columns are present
            assert "sell_p60" in output_df.columns
            assert "sell_hazard_daily" in output_df.columns

            # Check ladder columns are NOT present or are null
            if "sell_p60_ladder" in output_df.columns:
                assert pd.isna(output_df.iloc[0]["sell_p60_ladder"])
            if "sell_ladder_segments" in output_df.columns:
                assert pd.isna(output_df.iloc[0]["sell_ladder_segments"])

    def test_cli_ladder_uses_adjusted_hazard(self):
        """Test that ladder uses the adjusted hazard from base model."""
        runner = CliRunner()

        # Create items with different conditions to get different hazards
        test_data = pd.DataFrame(
            [
                {
                    "title": "New Item",
                    "condition": "New",
                    "category": "electronics",
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                },
                {
                    "title": "Used Item",
                    "condition": "Used - Fair",
                    "category": "electronics",
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test_input.csv"
            output_file = Path(tmp_dir) / "test_output.csv"

            test_data.to_csv(input_file, index=False)

            result = runner.invoke(
                main,
                [
                    str(input_file),
                    str(output_file),
                    "--survival-model",
                    "loglogistic",
                    "--use-pricing-ladder",
                ],
            )

            assert result.exit_code == 0
            output_df = pd.read_csv(output_file)

            # Different conditions should result in different hazards and sell-through
            new_item_p60 = output_df.iloc[0]["sell_p60_ladder"]
            used_item_p60 = output_df.iloc[1]["sell_p60_ladder"]

            # New item should generally have higher sell-through than used item
            assert new_item_p60 != used_item_p60
            assert 0.0 <= new_item_p60 <= 1.0
            assert 0.0 <= used_item_p60 <= 1.0
