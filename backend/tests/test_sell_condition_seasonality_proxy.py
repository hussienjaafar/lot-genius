"""Tests for sell-through proxy model condition and seasonality integration."""

from unittest.mock import patch

import pandas as pd
from lotgenius.sell import estimate_sell_p60


class TestSellConditionSeasonalityProxy:
    """Test condition and seasonality adjustments in proxy sell-through model."""

    @patch("lotgenius.sell._load_seasonality")
    def test_condition_velocity_adjustment(self, mock_load_seasonality):
        """Test condition affects velocity adjustment in proxy model."""
        # Mock seasonality data
        mock_load_seasonality.return_value = {
            "electronics": {"1": 1.1, "6": 0.9},  # Jan high, Jun low
            "default": {"1": 1.0, "6": 1.0},
        }

        row = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "Used - Good",  # Should normalize to used_good (0.85 factor)
                "category_1": "Electronics",
            }
        )

        # Create a test dataframe
        df = pd.DataFrame([row])

        # Test January (high season) - mock the seasonality and condition factors
        with patch("lotgenius.sell._get_seasonality_factor", return_value=1.1):
            result_df, events = estimate_sell_p60(df, days=30)

        # Check that condition and seasonality factors are applied correctly
        assert "sell_condition_factor" in result_df.columns
        assert "sell_seasonality_factor" in result_df.columns
        # Used good condition should have velocity factor < 1.0
        assert result_df.iloc[0]["sell_condition_factor"] < 1.0

    @patch("lotgenius.sell._load_seasonality")
    def test_new_condition_no_velocity_penalty(self, mock_load_seasonality):
        """Test new condition has no velocity penalty (factor 1.0)."""
        mock_load_seasonality.return_value = {
            "electronics": {"6": 0.9},
            "default": {"6": 1.0},
        }

        row = pd.Series(
            {
                "title": "iPhone 14",
                "condition": "New",  # Should get factor 1.0
                "category_1": "Electronics",
            }
        )

        # Create test dataframe
        df = pd.DataFrame([row])

        # Test June (low season)
        with patch("lotgenius.sell._get_seasonality_factor", return_value=0.9):
            result_df, events = estimate_sell_p60(df, days=30)

        # Check that new condition gets factor 1.0 and seasonality is applied
        assert result_df.iloc[0]["sell_condition_factor"] == 1.0
        assert result_df.iloc[0]["sell_seasonality_factor"] == 0.9

    @patch("lotgenius.sell._load_seasonality")
    def test_seasonality_default_fallback(self, mock_load_seasonality):
        """Test seasonality falls back to default for unknown categories."""
        mock_load_seasonality.return_value = {
            "electronics": {"1": 1.2},
            "default": {"1": 1.0, "6": 1.0},
        }

        row = pd.Series(
            {
                "title": "Random Item",
                "condition": "Like New",
                "category_1": "Unknown Category",  # Not in seasonality data
            }
        )

        df = pd.DataFrame([row])

        with patch("lotgenius.sell._get_seasonality_factor", return_value=1.0):
            result_df, events = estimate_sell_p60(df, days=30)

        # Should use default seasonality (1.0) with like_new condition factor
        assert result_df.iloc[0]["sell_seasonality_factor"] == 1.0
        # Check the condition factor is from CONDITION_VELOCITY_FACTOR settings
        from lotgenius.config import settings
        from lotgenius.normalize import condition_bucket

        expected_factor = settings.CONDITION_VELOCITY_FACTOR.get(
            condition_bucket(row), 1.0
        )
        assert result_df.iloc[0]["sell_condition_factor"] == expected_factor
