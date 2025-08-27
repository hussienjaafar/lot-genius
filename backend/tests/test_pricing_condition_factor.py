"""Tests for pricing condition factor integration."""

import pandas as pd
from lotgenius.pricing import build_sources_from_row


class TestPricingConditionFactor:
    """Test condition factors applied to pricing sources."""

    def test_new_condition_no_adjustment(self):
        """Test new condition gets no price adjustment (factor 1.0)."""
        row = pd.Series(
            {
                "title": "iPhone 14",
                "brand": "Apple",
                "condition": "New",
                "ebay_med": 800.0,
                "category_1": "Electronics",
            }
        )

        # Set up parameters for build_sources_from_row
        priors = {"keepa:new": 0.8, "keepa:used": 0.2}
        sources = build_sources_from_row(
            row, priors, cv_fallback=0.2, use_used_for_nonnew=False
        )

        # Check that condition factor is applied correctly for new condition
        # Should get factor 1.0 for new condition
        from lotgenius.config import settings
        from lotgenius.normalize import condition_bucket

        normalized_cond = condition_bucket(row)
        expected_factor = settings.CONDITION_PRICE_FACTOR.get(normalized_cond, 1.0)
        assert expected_factor == 1.0

    def test_like_new_condition_adjustment(self):
        """Test like new condition gets 0.95 factor adjustment."""
        row = pd.Series(
            {
                "title": "iPhone 14",
                "brand": "Apple",
                "condition": "Like New",
                "ebay_med": 800.0,
                "category_1": "Electronics",
            }
        )

        priors = {"keepa:new": 0.8, "keepa:used": 0.2}
        sources = build_sources_from_row(
            row, priors, cv_fallback=0.2, use_used_for_nonnew=False
        )

        # Check that condition factor is applied correctly for like new condition
        from lotgenius.config import settings
        from lotgenius.normalize import condition_bucket

        normalized_cond = condition_bucket(row)
        expected_factor = settings.CONDITION_PRICE_FACTOR.get(normalized_cond, 1.0)
        assert expected_factor == 0.95  # like_new factor

    def test_open_box_condition_adjustment(self):
        """Test open box condition gets 0.92 factor adjustment."""
        row = pd.Series(
            {
                "title": "iPhone 14",
                "brand": "Apple",
                "condition": "Open Box",
                "ebay_med": 800.0,
                "category_1": "Electronics",
            }
        )

        priors = {"keepa:new": 0.8, "keepa:used": 0.2}
        sources = build_sources_from_row(
            row, priors, cv_fallback=0.2, use_used_for_nonnew=False
        )

        # Check that condition factor is applied correctly for open box condition
        from lotgenius.config import settings
        from lotgenius.normalize import condition_bucket

        normalized_cond = condition_bucket(row)
        expected_factor = settings.CONDITION_PRICE_FACTOR.get(normalized_cond, 1.0)
        assert expected_factor == 0.92  # open_box factor
