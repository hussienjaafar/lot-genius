"""Test pricing ladder functionality."""

import math

from lotgenius.ladder import compute_ladder_sellthrough, pricing_ladder


class TestPricingLadder:
    """Test pricing ladder generation."""

    def test_pricing_ladder_basic(self):
        """Test basic pricing ladder generation."""
        segments = pricing_ladder(
            base_price=100.0,
            horizon_days=60,
            discount_day=21,
            discount_rate=0.10,
            clearance_day=45,
            clearance_fraction=0.50,
        )

        assert len(segments) == 3

        # Phase 1: Base price (days 0-20)
        assert segments[0]["day_from"] == 0
        assert segments[0]["day_to"] == 20
        assert segments[0]["price"] == 100.0

        # Phase 2: Discount price (days 21-44)
        assert segments[1]["day_from"] == 21
        assert segments[1]["day_to"] == 44
        assert segments[1]["price"] == 90.0  # 10% discount

        # Phase 3: Clearance price (days 45-60)
        assert segments[2]["day_from"] == 45
        assert segments[2]["day_to"] == 60
        assert segments[2]["price"] == 50.0  # 50% of base

    def test_pricing_ladder_short_horizon(self):
        """Test pricing ladder with horizon shorter than clearance day."""
        segments = pricing_ladder(
            base_price=100.0, horizon_days=30, discount_day=21, clearance_day=45
        )

        # Should only have base and discount phases
        assert len(segments) == 2
        assert segments[0]["day_to"] == 20
        assert segments[1]["day_from"] == 21
        assert segments[1]["day_to"] == 30

    def test_pricing_ladder_immediate_discount(self):
        """Test pricing ladder with immediate discount (day 0)."""
        segments = pricing_ladder(
            base_price=100.0, horizon_days=60, discount_day=0, clearance_day=30
        )

        # Should skip base phase
        assert len(segments) == 2
        assert segments[0]["day_from"] == 0
        assert segments[0]["day_to"] == 29
        assert segments[0]["price"] == 90.0  # Discount price

        assert segments[1]["day_from"] == 30
        assert segments[1]["price"] == 50.0  # Clearance price

    def test_pricing_ladder_no_discount_phase(self):
        """Test pricing ladder where discount_day equals clearance_day."""
        segments = pricing_ladder(
            base_price=100.0, horizon_days=60, discount_day=30, clearance_day=30
        )

        # Should skip discount phase
        assert len(segments) == 2
        assert segments[0]["day_from"] == 0
        assert segments[0]["day_to"] == 29
        assert segments[0]["price"] == 100.0  # Base price

        assert segments[1]["day_from"] == 30
        assert segments[1]["price"] == 50.0  # Clearance price

    def test_pricing_ladder_edge_cases(self):
        """Test pricing ladder edge cases."""
        # Very short horizon
        segments = pricing_ladder(base_price=100.0, horizon_days=1)
        assert len(segments) >= 1

        # Zero discount rate
        segments = pricing_ladder(base_price=100.0, discount_rate=0.0)
        if len(segments) >= 2:
            assert segments[1]["price"] == 100.0  # No discount

        # 100% clearance (free)
        segments = pricing_ladder(base_price=100.0, clearance_fraction=0.0)
        if len(segments) >= 3:
            assert segments[2]["price"] == 0.0


class TestComputeLadderSellthrough:
    """Test ladder sell-through computation."""

    def test_compute_ladder_sellthrough_basic(self):
        """Test basic ladder sell-through calculation."""
        segments = [
            {"day_from": 0, "day_to": 20, "price": 100.0},
            {"day_from": 21, "day_to": 44, "price": 90.0},
            {"day_from": 45, "day_to": 60, "price": 50.0},
        ]

        base_hazard = 0.01  # 1% daily hazard rate
        sellthrough = compute_ladder_sellthrough(segments, base_hazard)

        # Should be a probability between 0 and 1
        assert 0 <= sellthrough <= 1

        # With price drops, should be higher than flat pricing
        flat_sellthrough = 1.0 - math.exp(-base_hazard * 60)
        assert sellthrough > flat_sellthrough

    def test_compute_ladder_sellthrough_single_segment(self):
        """Test ladder sell-through with single segment."""
        segments = [{"day_from": 0, "day_to": 60, "price": 100.0}]

        base_hazard = 0.02
        sellthrough = compute_ladder_sellthrough(segments, base_hazard)

        # Should equal standard exponential model
        expected = 1.0 - math.exp(-base_hazard * 61)  # 61 days (0-60 inclusive)
        assert abs(sellthrough - expected) < 0.001

    def test_compute_ladder_sellthrough_empty_segments(self):
        """Test ladder sell-through with empty segments."""
        sellthrough = compute_ladder_sellthrough([], 0.01)
        assert sellthrough == 0.0

    def test_compute_ladder_sellthrough_price_elasticity(self):
        """Test that price changes affect sell-through via elasticity."""
        # Use a fixed reference price for comparison
        reference_price = 100.0
        base_hazard = 0.01

        # Lower price should increase sell-through
        low_price_segments = [
            {"day_from": 0, "day_to": 60, "price": 50.0}  # Half price
        ]

        high_price_segments = [
            {"day_from": 0, "day_to": 60, "price": 200.0}  # Double price
        ]

        low_sellthrough = compute_ladder_sellthrough(
            low_price_segments, base_hazard, reference_price=reference_price
        )
        high_sellthrough = compute_ladder_sellthrough(
            high_price_segments, base_hazard, reference_price=reference_price
        )

        # Lower price should result in higher sell-through
        assert low_sellthrough > high_sellthrough

    def test_compute_ladder_sellthrough_progressive_discounts(self):
        """Test that progressive discounts increase overall sell-through."""
        # Flat pricing
        flat_segments = [{"day_from": 0, "day_to": 60, "price": 100.0}]

        # Progressive discounts
        discount_segments = [
            {"day_from": 0, "day_to": 20, "price": 100.0},
            {"day_from": 21, "day_to": 40, "price": 80.0},
            {"day_from": 41, "day_to": 60, "price": 60.0},
        ]

        base_hazard = 0.015
        flat_sellthrough = compute_ladder_sellthrough(flat_segments, base_hazard)
        discount_sellthrough = compute_ladder_sellthrough(
            discount_segments, base_hazard
        )

        # Progressive discounts should increase sell-through
        assert discount_sellthrough > flat_sellthrough

    def test_compute_ladder_sellthrough_survival_probability(self):
        """Test that survival probability decreases correctly across segments."""
        segments = [
            {"day_from": 0, "day_to": 29, "price": 100.0},
            {"day_from": 30, "day_to": 59, "price": 50.0},  # 50% price drop
        ]

        base_hazard = 0.02
        sellthrough = compute_ladder_sellthrough(segments, base_hazard)

        # Should be bounded properly
        assert 0 < sellthrough < 1

        # Verify it's greater than either segment alone
        segment1_only = 1.0 - math.exp(-base_hazard * 30)
        segment2_hazard = base_hazard * (0.5**-0.5)  # Price elasticity effect
        segment2_only = 1.0 - math.exp(-segment2_hazard * 30)

        # Total should be greater than segment 1 alone
        assert sellthrough > segment1_only


class TestLadderIntegration:
    """Test integration scenarios."""

    def test_realistic_pricing_scenario(self):
        """Test realistic pricing scenario with default settings."""
        # Typical scenario: $100 item, 10% discount at day 21, 50% clearance at day 45
        segments = pricing_ladder(100.0)  # Use defaults

        assert len(segments) == 3
        assert segments[0]["price"] == 100.0
        assert segments[1]["price"] == 90.0
        assert segments[2]["price"] == 50.0

        # Compute sell-through with moderate hazard rate
        sellthrough = compute_ladder_sellthrough(segments, base_hazard_rate=0.008)

        # Should be reasonable probability (20-80%)
        assert 0.20 < sellthrough < 0.80

    def test_ladder_improves_sellthrough(self):
        """Test that ladder pricing improves sell-through vs flat pricing."""
        base_price = 150.0
        horizon_days = 60
        base_hazard = 0.005

        # Flat pricing
        flat_sellthrough = 1.0 - math.exp(-base_hazard * horizon_days)

        # Ladder pricing
        segments = pricing_ladder(base_price, horizon_days=horizon_days)
        ladder_sellthrough = compute_ladder_sellthrough(segments, base_hazard)

        # Ladder should improve sell-through
        improvement = ladder_sellthrough - flat_sellthrough
        assert improvement > 0
        assert improvement < 0.5  # But not unrealistically high

    def test_extreme_elasticity_bounds(self):
        """Test that extreme price changes don't cause unrealistic results."""
        # Very cheap pricing
        cheap_segments = [{"day_from": 0, "day_to": 60, "price": 1.0}]
        base_price = 100.0  # Implied from first segment comparison

        # Very expensive pricing
        expensive_segments = [{"day_from": 0, "day_to": 60, "price": 1000.0}]

        base_hazard = 0.01
        reference_price = 100.0  # Use common reference for comparison

        # Cheap should have high but bounded sell-through
        cheap_sellthrough = compute_ladder_sellthrough(
            cheap_segments, base_hazard, reference_price=reference_price
        )
        assert cheap_sellthrough <= 1.0

        # Expensive should have low but positive sell-through
        expensive_sellthrough = compute_ladder_sellthrough(
            expensive_segments, base_hazard, reference_price=reference_price
        )
        assert expensive_sellthrough > 0
        assert expensive_sellthrough < cheap_sellthrough
