"""Tests for basic survivorship model functionality and defaults."""

import pandas as pd
from lotgenius.config import settings
from lotgenius.survivorship import (
    _get_alpha_scale_category,
    _load_survival_alpha_scaling,
    estimate_sell_p60_survival,
)


class TestSurvivorshipBasic:
    """Test basic survivorship model functionality."""

    def test_default_survival_model_config(self):
        """Test that survival model is set as default in config."""
        assert settings.SURVIVAL_MODEL == "loglogistic"

    def test_survival_alpha_scaling_loading(self):
        """Test survival alpha scaling data loading."""
        scaling = _load_survival_alpha_scaling()
        assert isinstance(scaling, dict)
        assert "default" in scaling
        assert scaling["default"] == 1.0

    def test_category_alpha_scaling(self):
        """Test category-based alpha scaling."""
        # Test with electronics category
        row_electronics = pd.Series({"title": "iPhone 14", "category": "electronics"})
        scale_electronics = _get_alpha_scale_category(row_electronics)
        assert isinstance(scale_electronics, float)
        assert scale_electronics > 0

        # Test with unknown category (should use default)
        row_unknown = pd.Series({"title": "Unknown Item", "category": "Unknown"})
        scale_unknown = _get_alpha_scale_category(row_unknown)
        assert scale_unknown == 1.0

    def test_survivorship_basic_functionality(self):
        """Test basic survivorship model execution."""
        df = pd.DataFrame(
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

        result_df, events = estimate_sell_p60_survival(df, alpha=2.0, beta=1.0, days=60)

        # Check required columns are present
        required_cols = [
            "sell_p60",
            "sell_hazard_daily",
            "sell_ptm_z",
            "sell_alpha_used",
            "sell_beta_used",
            "sell_condition_used",
            "sell_seasonality_factor",
            "sell_alpha_scale_category",
        ]
        for col in required_cols:
            assert col in result_df.columns

        # Check values are reasonable
        assert 0.0 <= result_df.iloc[0]["sell_p60"] <= 1.0
        assert result_df.iloc[0]["sell_hazard_daily"] > 0
        assert result_df.iloc[0]["sell_alpha_used"] > 0
        assert result_df.iloc[0]["sell_beta_used"] > 0
        assert result_df.iloc[0]["sell_alpha_scale_category"] > 0

        # Check events are generated
        assert len(events) == 1
        assert events[0]["source"] == "sell:survival"
        assert "alpha_scale_category" in events[0]["meta"]

    def test_survivorship_category_scaling_applied(self):
        """Test that category scaling is actually applied to alpha."""
        # Create test data with known category
        df = pd.DataFrame(
            [
                {
                    "title": "Electronics Item",
                    "condition": "New",
                    "category": "electronics",  # Should get scaling factor 0.8
                    "est_price_mu": 100.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 100.0,
                }
            ]
        )

        result_df, events = estimate_sell_p60_survival(df, alpha=2.0, beta=1.0, days=60)

        # Check that alpha scaling was applied
        alpha_scale = result_df.iloc[0]["sell_alpha_scale_category"]
        alpha_used = result_df.iloc[0]["sell_alpha_used"]

        # Electronics should have scaling factor 0.8 (from data file)
        assert alpha_scale == 0.8

        # Alpha should be affected by the scaling (along with other factors)
        # Since scaling < 1.0, alpha should be reduced (faster selling)
        assert alpha_used != 2.0  # Should be modified from base alpha
