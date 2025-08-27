"""
Tests for confidence-aware evidence gating.

This module tests the adaptive threshold system that raises evidence requirements
for ambiguous items while preserving existing behavior for high-trust IDs.
"""

from unittest.mock import patch

from backend.lotgenius.gating import _ambiguity_flags, passes_evidence_gate


class TestAmbiguityFlags:
    """Test ambiguity flag detection."""

    def test_no_ambiguity_flags(self):
        """Clean item with specific title, brand, and condition should have no flags."""
        item = {
            "title": "iPhone 13 Pro Max 256GB Blue",
            "brand": "Apple",
            "condition": "New",
        }
        flags = _ambiguity_flags(item)
        assert flags == []

    def test_generic_title_flag(self):
        """Item with generic terms in title should get generic:title flag."""
        item = {
            "title": "Lot of 3 assorted electronics bundle pack",
            "brand": "Generic",
            "condition": "Used",
        }
        flags = _ambiguity_flags(item)
        assert "generic:title" in flags

    def test_ambiguous_brand_flag(self):
        """Item with missing brand should get ambiguous:brand flag (only with title)."""
        item = {"title": "iPhone 13 Pro Max", "condition": "New"}
        flags = _ambiguity_flags(item)
        assert "ambiguous:brand" in flags

        # Empty brand should also trigger flag
        item["brand"] = ""
        flags = _ambiguity_flags(item)
        assert "ambiguous:brand" in flags

        # But empty item should not trigger flag
        empty_item = {}
        flags = _ambiguity_flags(empty_item)
        assert "ambiguous:brand" not in flags

    def test_ambiguous_condition_flag(self):
        """Item with unknown condition should get ambiguous:condition flag."""
        item = {"title": "iPhone 13 Pro Max", "brand": "Apple"}

        # Missing condition no longer triggers flag (only explicit "unknown")
        flags = _ambiguity_flags(item)
        assert "ambiguous:condition" not in flags

        # Unknown condition should trigger flag
        item["condition"] = "Unknown"
        flags = _ambiguity_flags(item)
        assert "ambiguous:condition" in flags

        # Unspecified condition should trigger flag
        item["condition"] = "unspecified"
        flags = _ambiguity_flags(item)
        assert "ambiguous:condition" in flags

    def test_multiple_ambiguity_flags(self):
        """Item with multiple ambiguity issues should get multiple flags."""
        item = {
            "title": "Lot of broken electronics for parts",  # generic terms
            "condition": "Unknown",  # unknown condition
            # missing brand
        }
        flags = _ambiguity_flags(item)
        assert "generic:title" in flags
        assert "ambiguous:brand" in flags
        assert "ambiguous:condition" in flags
        assert len(flags) == 3


class TestConfidenceGating:
    """Test confidence-aware evidence gating functionality."""

    def test_non_ambiguous_passes_base_threshold(self):
        """Clean item should pass with base threshold (3 comps)."""
        item = {
            "title": "iPhone 13 Pro Max 256GB Blue",
            "brand": "Apple",
            "condition": "New",
        }
        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=3,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert result.passed
        assert result.core_included
        assert "comps:>=3" in result.tags
        assert "secondary:yes" in result.tags
        assert "conf:req_comps:3" in result.tags
        # Should have no ambiguity flags
        assert not any(
            tag.startswith("generic:") or tag.startswith("ambiguous:")
            for tag in result.tags
        )

    def test_ambiguous_requires_more_comps(self):
        """Ambiguous item should require more comps than base threshold."""
        # Missing brand + generic title = 2 flags, so needs 3+2=5 comps
        item = {
            "title": "Lot of assorted widgets bundle",  # generic title
            "condition": "New",
            # missing brand -> ambiguous:brand
        }

        # Should fail with base threshold (3 comps)
        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=3,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert not result.passed
        assert not result.core_included
        assert "comps:<5" in result.tags
        assert "generic:title" in result.tags
        assert "ambiguous:brand" in result.tags
        assert "conf:req_comps:5" in result.tags

        # Should pass with higher threshold (5 comps)
        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=5,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert result.passed
        assert result.core_included
        assert "comps:>=5" in result.tags
        assert "secondary:yes" in result.tags
        assert "generic:title" in result.tags
        assert "ambiguous:brand" in result.tags
        assert "conf:req_comps:5" in result.tags

    def test_unknown_condition_adds_bonus(self):
        """Unknown condition should add to required comps."""
        item = {
            "title": "iPhone 13 Pro Max",
            "brand": "Apple",
            "condition": "Unknown",  # 1 ambiguity flag -> needs 3+1=4 comps
        }

        # Should fail with base threshold (3 comps)
        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=3,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert not result.passed
        assert not result.core_included
        assert "comps:<4" in result.tags
        assert "ambiguous:condition" in result.tags
        assert "conf:req_comps:4" in result.tags

        # Should pass with 4 comps
        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=4,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert result.passed
        assert result.core_included
        assert "comps:>=4" in result.tags
        assert "ambiguous:condition" in result.tags
        assert "conf:req_comps:4" in result.tags

    def test_high_trust_id_bypass_ignores_ambiguity(self):
        """High-trust ID should bypass all ambiguity requirements."""
        item = {
            "title": "Lot of broken electronics for parts wholesale",  # Multiple flags
            "condition": "Unknown",
            # missing brand -> multiple ambiguity flags
        }

        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=0,  # No comps at all
            has_secondary_signal=False,  # No secondary signal
            has_high_trust_id=True,  # But high-trust ID bypasses everything
        )

        assert result.passed
        assert result.core_included
        assert "id:trusted" in result.tags
        assert result.reason == "High-trust ID present"

    def test_max_comps_cap_applied(self):
        """Required comps should be capped at EVIDENCE_MIN_COMPS_MAX."""
        item = {
            "title": "Lot of broken assorted generic wholesale bundle pieces for parts",  # Many flags
            "condition": "Unknown",
            # missing brand
        }

        # Mock settings to test cap behavior
        with patch("backend.lotgenius.gating.settings") as mock_settings:
            mock_settings.EVIDENCE_MIN_COMPS_BASE = 3
            mock_settings.EVIDENCE_AMBIGUITY_BONUS_PER_FLAG = 10  # High bonus
            mock_settings.EVIDENCE_MIN_COMPS_MAX = 5  # Low cap

            result = passes_evidence_gate(
                item,
                sold_comps_count_180d=4,
                has_secondary_signal=True,
                has_high_trust_id=False,
            )

            # Should require only 5 comps (capped) not 3 + 10*3 = 33
            assert "conf:req_comps:5" in result.tags
            assert not result.passed  # 4 < 5, should still fail

            # Should pass with exactly 5 comps
            result = passes_evidence_gate(
                item,
                sold_comps_count_180d=5,
                has_secondary_signal=True,
                has_high_trust_id=False,
            )

            assert result.passed
            assert "comps:>=5" in result.tags

    def test_secondary_signal_still_required(self):
        """Even with sufficient comps, secondary signal is still required."""
        item = {
            "title": "Lot of widgets bundle",  # 2 flags -> needs 3+2=5 comps
            # missing brand -> ambiguous:brand
        }

        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=10,  # Plenty of comps
            has_secondary_signal=False,  # But no secondary signal
            has_high_trust_id=False,
        )

        assert not result.passed
        assert not result.core_included
        assert "secondary:no" in result.tags
        assert "No secondary signals" in result.reason

    def test_legacy_tag_format_preserved(self):
        """Legacy 'comps:<3' tag should be preserved for non-ambiguous items."""
        item = {
            "title": "iPhone 13 Pro Max",
            "brand": "Apple",
            "condition": "New",  # No ambiguity flags -> requires base 3 comps
        }

        result = passes_evidence_gate(
            item,
            sold_comps_count_180d=2,
            has_secondary_signal=True,
            has_high_trust_id=False,
        )

        assert not result.passed
        assert "comps:<3" in result.tags  # Legacy format preserved
        assert "conf:req_comps:3" in result.tags
        assert "Insufficient comps" in result.reason

    def test_custom_settings_configuration(self):
        """Custom settings should affect threshold calculations."""
        item = {
            "title": "Widget lot",  # 1 flag (generic:title)
            "brand": "TestBrand",
            "condition": "New",
        }

        # Mock custom settings
        with patch("backend.lotgenius.gating.settings") as mock_settings:
            mock_settings.EVIDENCE_MIN_COMPS_BASE = 2  # Lower base
            mock_settings.EVIDENCE_AMBIGUITY_BONUS_PER_FLAG = 3  # Higher bonus
            mock_settings.EVIDENCE_MIN_COMPS_MAX = 8  # Higher cap

            # Should require 2 + 3*1 = 5 comps
            result = passes_evidence_gate(
                item,
                sold_comps_count_180d=4,
                has_secondary_signal=True,
                has_high_trust_id=False,
            )

            assert not result.passed
            assert "comps:<5" in result.tags
            assert "conf:req_comps:5" in result.tags

            # Should pass with 5 comps
            result = passes_evidence_gate(
                item,
                sold_comps_count_180d=5,
                has_secondary_signal=True,
                has_high_trust_id=False,
            )

            assert result.passed
            assert "comps:>=5" in result.tags
