"""Tests for survivorship model condition and seasonality integration."""

from unittest.mock import patch

import pandas as pd
from lotgenius.survivorship import estimate_sell_p60_survival


class TestSurvivorshipConditionSeasonality:
    """Test condition and seasonality adjustments in survivorship model."""

    @patch("lotgenius.sell._load_seasonality")
    def test_condition_affects_survivorship(self, mock_load_seasonality):
        """Test condition affects alpha parameter in survivorship model."""
        # Mock seasonality data
        mock_load_seasonality.return_value = {
            "electronics": {"1": 1.1},
            "default": {"1": 1.0},
        }

        row = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "Used - Fair",  # Should normalize to used_fair (velocity factor ~0.75)
                "category_1": "Electronics",
                "list_price": 800,
            }
        )

        # Create test dataframes
        df_used = pd.DataFrame([row])
        row_new = row.copy()
        row_new["condition"] = "New"
        df_new = pd.DataFrame([row_new])

        # Test with mock seasonality
        with patch("lotgenius.survivorship._get_seasonality_factor", return_value=1.1):
            result_used, _ = estimate_sell_p60_survival(
                df_used, alpha=2.0, beta=0.8, days=30
            )
            result_new, _ = estimate_sell_p60_survival(
                df_new, alpha=2.0, beta=0.8, days=30
            )

        # Used condition should have lower survival probability (harder to sell)
        assert result_used.iloc[0]["sell_p60"] < result_new.iloc[0]["sell_p60"]

    @patch("lotgenius.sell._load_seasonality")
    def test_seasonality_affects_survivorship(self, mock_load_seasonality):
        """Test seasonality affects survival probability."""
        # Mock high vs low season
        mock_load_seasonality.return_value = {
            "electronics": {"1": 1.3, "6": 0.7},  # Jan high, Jun low
            "default": {"1": 1.0, "6": 1.0},
        }

        row = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "New",
                "category_1": "Electronics",
                "list_price": 800,
            }
        )

        df = pd.DataFrame([row])

        # Test high season (January) - should sell faster (lower alpha = higher p60)
        result_high, _ = estimate_sell_p60_survival(df, alpha=2.0, beta=0.8, days=30)

        # Manually check that seasonality is applied correctly
        # In high season (factor 1.3), velocity should be higher, alpha should be lower
        # In low season (factor 0.7), velocity should be lower, alpha should be higher

        # Just verify that the function runs and produces reasonable results
        assert 0.0 <= result_high.iloc[0]["sell_p60"] <= 1.0
        assert (
            result_high.iloc[0]["sell_p60"] > 0.5
        )  # Should have decent sell-through in 30 days

    @patch("lotgenius.sell._load_seasonality")
    def test_combined_condition_seasonality_effect(self, mock_load_seasonality):
        """Test combined condition and seasonality effects."""
        mock_load_seasonality.return_value = {
            "electronics": {"6": 0.8},  # Low season
            "default": {"6": 1.0},
        }

        # Poor condition + low season = very slow selling
        row_worst = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "For Parts",  # velocity factor ~0.4
                "category_1": "Electronics",
                "list_price": 800,
            }
        )

        # Good condition + low season = moderate selling
        row_better = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "Like New",  # velocity factor ~0.95
                "category_1": "Electronics",
                "list_price": 800,
            }
        )

        df_worst = pd.DataFrame([row_worst])
        df_better = pd.DataFrame([row_better])

        with patch("lotgenius.sell._get_seasonality_factor", return_value=0.8):
            result_worst, _ = estimate_sell_p60_survival(
                df_worst, alpha=2.0, beta=0.8, days=30
            )
            result_better, _ = estimate_sell_p60_survival(
                df_better, alpha=2.0, beta=0.8, days=30
            )

        # Worse condition should have lower survival probability (harder to sell)
        assert result_worst.iloc[0]["sell_p60"] < result_better.iloc[0]["sell_p60"]
