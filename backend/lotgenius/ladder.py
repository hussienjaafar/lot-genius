"""Pricing ladder functionality for dynamic pricing schedules."""

from typing import Dict, List

from .config import settings


def pricing_ladder(
    base_price: float,
    horizon_days: int = None,
    discount_day: int = 21,
    discount_rate: float = 0.10,
    clearance_day: int = 45,
    clearance_fraction: float = None,
) -> List[Dict[str, float]]:
    """
    Generate a pricing ladder schedule with base price, discount, and clearance phases.

    Args:
        base_price: Starting price (e.g., P50 day 0)
        horizon_days: Total horizon for pricing (defaults to SELLTHROUGH_HORIZON_DAYS)
        discount_day: Day to start discount (default: 21)
        discount_rate: Discount percentage as decimal (default: 0.10 = 10%)
        clearance_day: Day to start clearance (default: 45)
        clearance_fraction: Clearance price as fraction of base (defaults to CLEARANCE_VALUE_AT_HORIZON)

    Returns:
        List of dicts with keys: day_from, day_to, price, hazard_multiplier

    Example:
        >>> ladder = pricing_ladder(100.0)
        >>> # Returns segments like:
        >>> # [{'day_from': 0, 'day_to': 20, 'price': 100.0},
        >>> #  {'day_from': 21, 'day_to': 44, 'price': 90.0},
        >>> #  {'day_from': 45, 'day_to': 60, 'price': 50.0}]
    """
    if horizon_days is None:
        horizon_days = settings.SELLTHROUGH_HORIZON_DAYS

    if clearance_fraction is None:
        clearance_fraction = settings.CLEARANCE_VALUE_AT_HORIZON

    # Calculate prices for each phase
    discount_price = base_price * (1.0 - discount_rate)
    clearance_price = base_price * clearance_fraction

    segments = []

    # Phase 1: Base price (day 0 to discount_day - 1)
    if discount_day > 0:
        segments.append(
            {
                "day_from": 0,
                "day_to": discount_day - 1,
                "days": (discount_day - 1) - 0 + 1,
                "price": base_price,
                # At reference/base price, multiplier is 1.0
                "hazard_multiplier": 1.0,
            }
        )

    # Phase 2: Discount price (discount_day to min(clearance_day - 1, horizon_days))
    if clearance_day > discount_day and horizon_days >= discount_day:
        _to = min(clearance_day - 1, horizon_days)
        segments.append(
            {
                "day_from": discount_day,
                "day_to": _to,
                "days": _to - discount_day + 1,
                "price": discount_price,
                # Default elasticity used here to provide a helpful hint for UIs/tests
                "hazard_multiplier": (discount_price / base_price) ** (-0.5),
            }
        )

    # Phase 3: Clearance price (clearance_day to horizon)
    if horizon_days >= clearance_day:
        segments.append(
            {
                "day_from": clearance_day,
                "day_to": horizon_days,
                "days": horizon_days - clearance_day + 1,
                "price": clearance_price,
                "hazard_multiplier": (clearance_price / base_price) ** (-0.5),
            }
        )

    return segments


def compute_ladder_sellthrough(
    ladder_segments: List[Dict[str, float]],
    base_hazard_rate: float,
    price_elasticity: float = -0.5,
    reference_price: float = None,
) -> float:
    """
    Compute expected sell-through across pricing ladder segments.

    Args:
        ladder_segments: List of pricing segments from pricing_ladder()
        base_hazard_rate: Base daily hazard rate at reference price
        price_elasticity: Price elasticity of demand (default: -0.5)
        reference_price: Reference price for elasticity (defaults to first segment price)

    Returns:
        Total expected sell-through probability across all segments

    The model assumes:
    - Price changes affect hazard rate via elasticity: λ_new = λ_base * (P_new/P_ref)^elasticity
    - Sell-through in each segment follows exponential model with adjusted hazard rate
    - Total sell-through is sum across segments, accounting for survival from previous segments
    """
    if not ladder_segments:
        return 0.0

    # Use reference price for elasticity calculations (defaults to first segment)
    if reference_price is None:
        reference_price = ladder_segments[0]["price"]

    total_sellthrough = 0.0
    survival_prob = 1.0  # Probability of not selling in previous segments

    for segment in ladder_segments:
        # Adjust hazard rate based on price elasticity
        price_ratio = segment["price"] / reference_price
        adjusted_hazard = base_hazard_rate * (price_ratio**price_elasticity)

        # Duration of this segment
        duration = segment["day_to"] - segment["day_from"] + 1

        # Probability of selling in this segment (given survival to this point)
        segment_sell_prob = 1.0 - exp(-adjusted_hazard * duration)

        # Add contribution to total sell-through
        total_sellthrough += survival_prob * segment_sell_prob

        # Update survival probability for next segment
        survival_prob *= 1.0 - segment_sell_prob

    return min(total_sellthrough, 1.0)


def exp(x: float) -> float:
    """Simple exponential function implementation."""
    import math

    return math.exp(x)
