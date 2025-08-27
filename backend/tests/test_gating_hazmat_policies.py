"""Test core brand gating and hazmat policy logic."""

import pytest
from lotgenius.gating import passes_evidence_gate


@pytest.fixture
def sample_items():
    """Sample items with various brand and hazmat characteristics."""
    return [
        {
            "sku_local": "APPLE_001",
            "brand": "Apple",
            "hazmat": False,
            "asin": "B08N5WRWNW",
            "keepa_new_count": 50,
        },
        {
            "sku_local": "SAMSUNG_002",
            "brand": "Samsung",
            "hazmat": False,
            "upc": "123456789012",
            "keepa_used_count": 30,
        },
        {
            "sku_local": "BATTERY_003",
            "brand": "Generic",
            "hazmat": True,
            "ean": "1234567890123",
            "keepa_new_count": 10,
        },
        {
            "sku_local": "NONAME_004",
            "brand": "",
            "hazmat": False,
            "keepa_new_count": 5,
        },
    ]


class TestBrandGating:
    """Test brand gating functionality."""

    def test_brand_gate_with_gated_brands(self, sample_items, monkeypatch):
        """Test brand gating with brands in gated list."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple,Samsung")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        apple_item = sample_items[0]
        samsung_item = sample_items[1]
        generic_item = sample_items[2]

        # Gated brands should be excluded from core
        apple_result = passes_evidence_gate(apple_item, 50, True, True)
        assert not apple_result.core_included
        assert "Brand gated" in apple_result.reason

        samsung_result = passes_evidence_gate(samsung_item, 30, True, True)
        assert not samsung_result.core_included
        assert "Brand gated" in samsung_result.reason

        # Non-gated brands should pass (with good evidence)
        generic_result = passes_evidence_gate(generic_item, 10, True, True)
        assert generic_result.core_included

    def test_brand_gate_with_empty_gated_list(self, sample_items, monkeypatch):
        """Test brand gating with empty gated brands list."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        # All brands should pass when no brands are gated (with good evidence)
        for item in sample_items:
            result = passes_evidence_gate(item, 50, True, True)
            assert result.core_included

    def test_brand_gate_case_insensitive(self, sample_items, monkeypatch):
        """Test brand gating is case insensitive."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "apple,SAMSUNG")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        apple_item = sample_items[0]  # brand: "Apple"
        samsung_item = sample_items[1]  # brand: "Samsung"

        # Should fail even with different case
        apple_result = passes_evidence_gate(apple_item, 50, True, True)
        assert not apple_result.core_included

        samsung_result = passes_evidence_gate(samsung_item, 30, True, True)
        assert not samsung_result.core_included

    def test_brand_gate_with_missing_brand(self, sample_items, monkeypatch):
        """Test brand gating with missing brand field."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        noname_item = sample_items[3]  # brand: ""

        # Empty brand should pass (not gated)
        result = passes_evidence_gate(noname_item, 5, True, True)
        assert result.core_included


class TestHazmatPolicies:
    """Test hazmat policy functionality."""

    def test_hazmat_policy_exclude(self, sample_items, monkeypatch):
        """Test hazmat policy exclude - hazmat items should fail."""
        monkeypatch.setenv("HAZMAT_POLICY", "exclude")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        non_hazmat = sample_items[0]  # hazmat: False
        hazmat_item = sample_items[2]  # hazmat: True

        # Non-hazmat should pass (with good evidence)
        non_hazmat_result = passes_evidence_gate(non_hazmat, 50, True, True)
        assert non_hazmat_result.core_included

        # Hazmat should be excluded
        hazmat_result = passes_evidence_gate(hazmat_item, 10, True, True)
        assert not hazmat_result.core_included
        assert "Hazmat excluded" in hazmat_result.reason

    def test_hazmat_policy_allow(self, sample_items, monkeypatch):
        """Test hazmat policy allow - all items should pass."""
        monkeypatch.setenv("HAZMAT_POLICY", "allow")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        # All items should pass regardless of hazmat status (with good evidence)
        for item in sample_items:
            result = passes_evidence_gate(item, 50, True, True)
            assert result.core_included

    def test_hazmat_policy_review(self, sample_items, monkeypatch):
        """Test hazmat policy review - hazmat items allowed but tagged."""
        monkeypatch.setenv("HAZMAT_POLICY", "review")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        non_hazmat = sample_items[0]  # hazmat: False
        hazmat_item = sample_items[2]  # hazmat: True

        # Non-hazmat items should pass normally
        non_hazmat_result = passes_evidence_gate(non_hazmat, 50, True, True)
        assert non_hazmat_result.core_included

        # Hazmat items should pass but be tagged for review
        hazmat_result = passes_evidence_gate(hazmat_item, 10, True, True)
        assert hazmat_result.core_included
        assert "hazmat:review" in hazmat_result.tags

    def test_hazmat_gate_missing_field(self, sample_items, monkeypatch):
        """Test hazmat gating with missing is_hazmat field."""
        monkeypatch.setenv("HAZMAT_POLICY", "exclude")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        # Item without is_hazmat field
        item_no_hazmat = {"sku_local": "TEST_001", "brand": "Test"}

        # Should pass (assume non-hazmat when field missing)
        result = passes_evidence_gate(item_no_hazmat, 50, True, True)
        assert result.core_included


class TestCombinedGating:
    """Test combined brand and hazmat gating through evidence gate."""

    def test_evidence_gate_combined_policies(self, sample_items, monkeypatch):
        """Test evidence gate with both brand and hazmat policies."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")
        monkeypatch.setenv("HAZMAT_POLICY", "exclude")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        apple_item = sample_items[0]  # Apple, non-hazmat
        samsung_item = sample_items[1]  # Samsung, non-hazmat
        battery_item = sample_items[2]  # Generic, hazmat

        # Apple item should be gated (gated brand)
        gate_result = passes_evidence_gate(
            apple_item,
            sold_comps_count_180d=50,
            has_secondary_signal=True,
            has_high_trust_id=True,
        )
        assert not gate_result.core_included

        # Samsung item should pass (not gated brand, not hazmat)
        gate_result = passes_evidence_gate(
            samsung_item,
            sold_comps_count_180d=30,
            has_secondary_signal=True,
            has_high_trust_id=True,
        )
        assert gate_result.core_included

        # Battery item should be gated (hazmat with exclude policy)
        gate_result = passes_evidence_gate(
            battery_item,
            sold_comps_count_180d=10,
            has_secondary_signal=True,
            has_high_trust_id=True,
        )
        assert not gate_result.core_included

    def test_evidence_gate_review_over_exclude(self, sample_items, monkeypatch):
        """Test that review policy allows items through core but flags them."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "")
        monkeypatch.setenv("HAZMAT_POLICY", "review")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        battery_item = sample_items[2]  # Generic, hazmat

        # With review policy, hazmat items should be allowed through but tagged
        gate_result = passes_evidence_gate(
            battery_item,
            sold_comps_count_180d=10,
            has_secondary_signal=True,
            has_high_trust_id=True,
        )
        assert gate_result.core_included  # Should pass through
        assert "hazmat:review" in gate_result.tags  # But tagged for review

    def test_evidence_gate_allow_policy(self, sample_items, monkeypatch):
        """Test that allow policy lets hazmat items through."""
        monkeypatch.setenv("GATED_BRANDS_CSV", "")
        monkeypatch.setenv("HAZMAT_POLICY", "allow")

        # Force reload of settings
        import lotgenius.config
        import lotgenius.gating
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()
        import importlib

        importlib.reload(lotgenius.gating)

        battery_item = sample_items[2]  # Generic, hazmat

        # With allow policy, hazmat items should pass
        gate_result = passes_evidence_gate(
            battery_item,
            sold_comps_count_180d=10,
            has_secondary_signal=True,
            has_high_trust_id=True,
        )
        assert gate_result.core_included
