"""Test report_lot.py pricing ladder section functionality."""

import json

import pandas as pd
import pytest
from click.testing import CliRunner

from backend.lotgenius.cli.report_lot import _mk_markdown, main


@pytest.fixture
def sample_items_with_ladder():
    """Create sample items DataFrame with ladder data."""
    return pd.DataFrame(
        [
            {
                "sku_local": "LADDER_001",
                "est_price_mu": 100.0,
                "est_price_p50": 95.0,
                "sell_p60": 0.75,
                "sell_p60_ladder": 0.75,
                "sell_ladder_segments": json.dumps(
                    [
                        {"day_from": 0, "day_to": 20, "price": 95.0},
                        {"day_from": 21, "day_to": 44, "price": 85.5},
                        {"day_from": 45, "day_to": 60, "price": 47.5},
                    ]
                ),
            },
            {
                "sku_local": "LADDER_002",
                "est_price_mu": 150.0,
                "est_price_p50": 140.0,
                "sell_p60": 0.68,
                "sell_p60_ladder": 0.68,
                "sell_ladder_segments": json.dumps(
                    [
                        {"day_from": 0, "day_to": 20, "price": 140.0},
                        {"day_from": 21, "day_to": 44, "price": 126.0},
                        {"day_from": 45, "day_to": 60, "price": 70.0},
                    ]
                ),
            },
            {
                "sku_local": "NO_LADDER_003",
                "est_price_mu": 200.0,
                "est_price_p50": 190.0,
                "sell_p60": 0.60,
                "sell_p60_ladder": None,
                "sell_ladder_segments": None,
            },
        ]
    )


@pytest.fixture
def sample_items_no_ladder():
    """Create sample items DataFrame without ladder data."""
    return pd.DataFrame(
        [
            {
                "sku_local": "STANDARD_001",
                "est_price_mu": 100.0,
                "est_price_p50": 95.0,
                "sell_p60": 0.65,
            },
            {
                "sku_local": "STANDARD_002",
                "est_price_mu": 150.0,
                "est_price_p50": 140.0,
                "sell_p60": 0.55,
            },
        ]
    )


@pytest.fixture
def sample_opt_result():
    """Create sample optimizer result."""
    return {
        "bid": 1000.0,
        "roi_p50": 1.5,
        "prob_roi_ge_target": 0.8,
        "expected_cash_60d": 1200.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.7,
    }


class TestReportLadderSection:
    """Test pricing ladder section in report generation."""

    def test_markdown_with_ladder_data(
        self, sample_items_with_ladder, sample_opt_result
    ):
        """Test markdown generation includes ladder section when data present."""
        markdown = _mk_markdown(sample_items_with_ladder, sample_opt_result)

        # Should include Pricing Ladder section
        assert "## Pricing Ladder" in markdown
        assert "Items with Ladder Pricing:" in markdown
        assert "Ladder Avg Sell-through (60d):" in markdown
        assert "Standard Avg Sell-through (60d):" in markdown
        assert "Sample Pricing Schedule:" in markdown

        # Should show correct counts
        assert "2 (66.7%)" in markdown  # 2 out of 3 items have ladder data

        # Should show pricing schedule
        assert "Days 0-20: $95.00" in markdown
        assert "Days 21-44: $85.50" in markdown
        assert "Days 45-60: $47.50" in markdown

    def test_markdown_without_ladder_data(
        self, sample_items_no_ladder, sample_opt_result
    ):
        """Test markdown generation excludes ladder section when no data."""
        markdown = _mk_markdown(sample_items_no_ladder, sample_opt_result)

        # Should NOT include Pricing Ladder section
        assert "## Pricing Ladder" not in markdown
        assert "Items with Ladder Pricing:" not in markdown
        assert "Sample Pricing Schedule:" not in markdown

    def test_markdown_partial_ladder_data(self, sample_opt_result):
        """Test markdown with some items having ladder data."""
        # Mix of items with and without ladder data
        items = pd.DataFrame(
            [
                {
                    "sku_local": "WITH_LADDER",
                    "sell_p60": 0.75,
                    "sell_ladder_segments": json.dumps(
                        [
                            {"day_from": 0, "day_to": 30, "price": 100.0},
                            {"day_from": 31, "day_to": 60, "price": 50.0},
                        ]
                    ),
                },
                {
                    "sku_local": "NO_LADDER",
                    "sell_p60": 0.60,
                    "sell_ladder_segments": None,
                },
                {
                    "sku_local": "EMPTY_LADDER",
                    "sell_p60": 0.55,
                    "sell_ladder_segments": "",
                },
            ]
        )

        markdown = _mk_markdown(items, sample_opt_result)

        # Should include section since at least one item has ladder data
        assert "## Pricing Ladder" in markdown
        assert "1 (33.3%)" in markdown  # 1 out of 3 items

    def test_ladder_section_positioning(
        self, sample_items_with_ladder, sample_opt_result
    ):
        """Test that ladder section appears in correct position."""
        markdown = _mk_markdown(sample_items_with_ladder, sample_opt_result)

        # Find section positions
        ladder_pos = markdown.find("## Pricing Ladder")
        investment_pos = markdown.find("## Investment Decision")

        # Ladder should come before Investment Decision
        assert ladder_pos < investment_pos
        assert ladder_pos > 0
        assert investment_pos > 0

    def test_ladder_metrics_calculation(self, sample_opt_result):
        """Test ladder metrics calculation accuracy."""
        items = pd.DataFrame(
            [
                {
                    "sell_p60": 0.8,
                    "sell_ladder_segments": json.dumps([]),
                },  # With ladder
                {
                    "sell_p60": 0.7,
                    "sell_ladder_segments": json.dumps([]),
                },  # With ladder
                {"sell_p60": 0.6, "sell_ladder_segments": None},  # No ladder
                {"sell_p60": 0.5, "sell_ladder_segments": None},  # No ladder
            ]
        )

        markdown = _mk_markdown(items, sample_opt_result)

        # Calculate expected metrics
        ladder_avg = (0.8 + 0.7) / 2  # 0.75 = 75%
        standard_avg = (0.6 + 0.5) / 2  # 0.55 = 55%

        assert "75.0%" in markdown  # Ladder average
        assert "55.0%" in markdown  # Standard average
        assert "2 (50.0%)" in markdown  # 2 out of 4 items

    def test_malformed_ladder_segments(self, sample_opt_result):
        """Test handling of malformed ladder segment data."""
        items = pd.DataFrame(
            [
                {
                    "sku_local": "MALFORMED",
                    "sell_p60": 0.6,
                    "sell_ladder_segments": "invalid json",
                },
                {
                    "sku_local": "GOOD",
                    "sell_p60": 0.7,
                    "sell_ladder_segments": json.dumps(
                        [{"day_from": 0, "day_to": 60, "price": 100.0}]
                    ),
                },
            ]
        )

        markdown = _mk_markdown(items, sample_opt_result)

        # Should still include section and handle gracefully
        assert "## Pricing Ladder" in markdown
        assert "1 (50.0%)" in markdown  # Only 1 valid item

        # Should show sample from valid item
        assert "Days 0-60: $100.00" in markdown


class TestReportCLIWithLadder:
    """Test report CLI with ladder data."""

    def test_cli_report_with_ladder_csv(self, tmp_path):
        """Test CLI report generation with ladder-enabled CSV."""
        # Create items CSV with ladder data
        items_data = [
            {
                "sku_local": "ITEM_001",
                "est_price_mu": 100.0,
                "est_price_p50": 95.0,
                "sell_p60": 0.75,
                "sell_ladder_segments": json.dumps(
                    [
                        {"day_from": 0, "day_to": 20, "price": 95.0},
                        {"day_from": 21, "day_to": 44, "price": 85.5},
                        {"day_from": 45, "day_to": 60, "price": 47.5},
                    ]
                ),
            }
        ]

        items_csv = tmp_path / "items.csv"
        pd.DataFrame(items_data).to_csv(items_csv, index=False)

        # Create optimizer JSON
        opt_data = {
            "bid": 500.0,
            "roi_p50": 1.4,
            "prob_roi_ge_target": 0.75,
            "expected_cash_60d": 600.0,
            "meets_constraints": True,
        }

        opt_json = tmp_path / "opt.json"
        with open(opt_json, "w") as f:
            json.dump(opt_data, f)

        # Generate report
        out_markdown = tmp_path / "report.md"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(items_csv),
                "--opt-json",
                str(opt_json),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_markdown.exists()

        # Verify report content
        content = out_markdown.read_text()
        assert "## Pricing Ladder" in content
        assert "Items with Ladder Pricing:" in content
        assert "Sample Pricing Schedule:" in content

    def test_cli_report_without_ladder_csv(self, tmp_path):
        """Test CLI report generation with standard CSV (no ladder)."""
        # Create items CSV without ladder data
        items_data = [
            {
                "sku_local": "ITEM_001",
                "est_price_mu": 100.0,
                "est_price_p50": 95.0,
                "sell_p60": 0.65,
            }
        ]

        items_csv = tmp_path / "items.csv"
        pd.DataFrame(items_data).to_csv(items_csv, index=False)

        # Create optimizer JSON
        opt_data = {
            "bid": 500.0,
            "roi_p50": 1.4,
            "prob_roi_ge_target": 0.75,
            "expected_cash_60d": 600.0,
            "meets_constraints": True,
        }

        opt_json = tmp_path / "opt.json"
        with open(opt_json, "w") as f:
            json.dump(opt_data, f)

        # Generate report
        out_markdown = tmp_path / "report.md"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--items-csv",
                str(items_csv),
                "--opt-json",
                str(opt_json),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_markdown.exists()

        # Verify report content excludes ladder section
        content = out_markdown.read_text()
        assert "## Pricing Ladder" not in content
        assert "Items with Ladder Pricing:" not in content


class TestLadderSectionEdgeCases:
    """Test edge cases for ladder section."""

    def test_empty_items_dataframe(self, sample_opt_result):
        """Test with empty items DataFrame."""
        items = pd.DataFrame()
        markdown = _mk_markdown(items, sample_opt_result)

        # Should not include ladder section
        assert "## Pricing Ladder" not in markdown

    def test_all_null_ladder_segments(self, sample_opt_result):
        """Test with all items having null ladder segments."""
        items = pd.DataFrame(
            [
                {
                    "sku_local": "NULL_001",
                    "sell_p60": 0.6,
                    "sell_ladder_segments": None,
                },
                {
                    "sku_local": "NULL_002",
                    "sell_p60": 0.7,
                    "sell_ladder_segments": None,
                },
            ]
        )

        markdown = _mk_markdown(items, sample_opt_result)
        assert "## Pricing Ladder" not in markdown

    def test_missing_sell_p60_column(self, sample_opt_result):
        """Test with missing sell_p60 column."""
        items = pd.DataFrame(
            [
                {
                    "sku_local": "NO_P60",
                    "sell_ladder_segments": json.dumps(
                        [{"day_from": 0, "day_to": 60, "price": 100.0}]
                    ),
                }
            ]
        )

        markdown = _mk_markdown(items, sample_opt_result)

        # Should still include section but handle missing data gracefully
        assert "## Pricing Ladder" in markdown
        assert "1 (100.0%)" in markdown
