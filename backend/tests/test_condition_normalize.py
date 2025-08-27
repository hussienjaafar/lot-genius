"""Tests for condition normalization functionality."""

from lotgenius.normalize import normalize_condition


class TestConditionNormalize:
    """Test condition normalization edge cases and precedence."""

    def test_new_conditions(self):
        """Test various new condition formats."""
        assert normalize_condition("New") == "new"
        assert normalize_condition("NEW") == "new"
        assert normalize_condition("Brand New") == "new"
        assert normalize_condition("Factory New") == "new"

    def test_like_new_precedence(self):
        """Test like new takes precedence over generic new."""
        assert normalize_condition("Like New") == "like_new"
        assert normalize_condition("LIKE NEW") == "like_new"
        assert normalize_condition("Mint Condition") == "like_new"
        assert normalize_condition("Pristine") == "like_new"

    def test_open_box_precedence(self):
        """Test open box takes precedence over generic new."""
        assert normalize_condition("Open Box") == "open_box"
        assert normalize_condition("OPEN BOX") == "open_box"
        assert normalize_condition("OpenBox") == "open_box"
        assert normalize_condition("Display Model") == "open_box"
        assert normalize_condition("Demo Unit") == "open_box"

    def test_refurbished_precedence(self):
        """Test refurbished/renewed takes precedence over generic new."""
        assert normalize_condition("Refurbished") == "used_good"
        assert normalize_condition("REFURBISHED") == "used_good"
        assert normalize_condition("Renewed") == "used_good"
        assert normalize_condition("RENEWED") == "used_good"
        assert normalize_condition("Certified Refurbished") == "used_good"

    def test_used_conditions(self):
        """Test used condition variants."""
        assert normalize_condition("Used") == "used_good"
        assert normalize_condition("Good") == "used_good"
        assert normalize_condition("Used - Good") == "used_good"
        assert normalize_condition("Fair") == "used_fair"
        assert normalize_condition("Used - Fair") == "used_fair"
        assert normalize_condition("Acceptable") == "used_fair"

    def test_for_parts_conditions(self):
        """Test for parts/not working conditions."""
        assert normalize_condition("For Parts") == "for_parts"
        assert normalize_condition("FOR PARTS") == "for_parts"
        assert normalize_condition("Not Working") == "for_parts"
        assert normalize_condition("Broken") == "for_parts"
        assert normalize_condition("Salvage") == "for_parts"

    def test_unknown_conditions(self):
        """Test unknown/unrecognized conditions."""
        assert normalize_condition("") == "unknown"
        assert normalize_condition("   ") == "unknown"
        assert normalize_condition("Random String") == "unknown"
        assert normalize_condition("XYZ123") == "unknown"

    def test_edge_cases(self):
        """Test edge cases and complex strings."""
        # Test that "New" in middle doesn't match when more specific exists
        assert normalize_condition("Apple iPhone 12 Pro Max - Renewed") == "used_good"
        assert (
            normalize_condition("Samsung Galaxy - Open Box - New Condition")
            == "open_box"
        )
        assert normalize_condition("Like New in Original Box") == "like_new"

        # Test whitespace handling
        assert normalize_condition("  New  ") == "new"
        assert normalize_condition("\tRefurbished\n") == "used_good"

        # Test punctuation
        assert normalize_condition("New!") == "new"
        assert normalize_condition("Like-New") == "like_new"
        assert normalize_condition("Open/Box") == "open_box"
