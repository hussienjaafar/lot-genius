"""
Condition normalization utilities for standardizing item conditions.

Maps various condition descriptions to standard buckets for consistent
pricing and velocity adjustments across the pipeline.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Union

import pandas as pd


def normalize_condition(raw: str) -> str:
    """
    Normalize raw condition string to standard buckets.

    Standard buckets:
    - new: Brand new, sealed, never opened
    - like_new: Like new, mint, pristine
    - open_box: Open box, display model
    - used_good: Used in good/very good condition
    - used_fair: Used in fair/acceptable condition
    - for_parts: For parts, not working, damaged
    - unknown: Cannot determine condition

    Args:
        raw: Raw condition string

    Returns:
        Normalized condition bucket
    """
    if not raw:
        return "unknown"

    # Clean and lowercase the input
    cleaned = str(raw).strip().lower()

    # Remove extra spaces and normalize separators
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[_\-/]+", " ", cleaned)

    # Check for open box first (more specific than "new")
    if any(
        term in cleaned
        for term in [
            "open box",
            "openbox",
            "display",
            "demo",
            "floor model",
            "new other",
            "new(other)",
            "new (other)",
        ]
    ):
        return "open_box"

    # Check for like new conditions (more specific than "new")
    if any(
        term in cleaned
        for term in [
            "like new",
            "likenew",
            "mint",
            "pristine",
            "excellent",
            "near new",
            "barely used",
            "lightly used",
        ]
    ):
        return "like_new"

    # Check for refurbished/renewed first (before generic "new" check)
    if any(
        term in cleaned
        for term in ["refurbished", "refurb", "reconditioned", "renewed", "certified"]
    ):
        return "used_good"

    # Check for new conditions (after more specific checks)
    if any(
        term in cleaned
        for term in ["brand new", "sealed", "unopened", "bnib", "nib", "bnwt", "nwt"]
    ) or (
        "new" in cleaned
        and not any(
            qualifier in cleaned
            for qualifier in [
                "like",
                "other",
                "open",
                "used",
                "refurb",
                "excellent",
                "mint",
                "pristine",
                "renewed",
            ]
        )
    ):
        return "new"

    # (These checks moved above)

    # Check for parts/not working
    if any(
        term in cleaned
        for term in [
            "parts",
            "repair",
            "not working",
            "broken",
            "damaged",
            "defective",
            "faulty",
            "as is",
            "asis",
            "salvage",
            "scrap",
            "junk",
        ]
    ):
        return "for_parts"

    # (Refurbished check moved above to avoid "new" conflict)

    # Check for used conditions
    if "used" in cleaned or "pre owned" in cleaned or "preowned" in cleaned:
        # Check for good/very good
        if any(
            term in cleaned
            for term in ["good", "very good", "great", "vg", "v good", "v.good"]
        ):
            return "used_good"
        # Check for fair/acceptable
        if any(
            term in cleaned
            for term in ["fair", "acceptable", "ok", "okay", "average", "moderate"]
        ):
            return "used_fair"
        # Generic used defaults to good
        return "used_good"

    # Check for standalone condition descriptors
    if any(term in cleaned for term in ["good", "very good", "great", "vg"]):
        return "used_good"
    if any(term in cleaned for term in ["fair", "acceptable", "ok", "okay"]):
        return "used_fair"

    # Check for customer returns (context matters, default to open_box)
    if any(term in cleaned for term in ["return", "customer return", "returned"]):
        # If damaged, go to parts
        if any(term in cleaned for term in ["damaged", "broken", "defective"]):
            return "for_parts"
        # Otherwise treat as open box
        return "open_box"

    # Default fallback
    return "unknown"


def condition_bucket(row_or_dict: Union[pd.Series, Dict[str, Any]]) -> str:
    """
    Extract and normalize condition from a row or dictionary.

    Checks multiple fields in priority order:
    1. 'condition' field
    2. 'condition_detail' field
    3. 'notes' field for condition hints
    4. 'item_condition' field

    Args:
        row_or_dict: DataFrame row or dictionary with item data

    Returns:
        Normalized condition bucket
    """
    # Convert to dict if it's a Series
    if isinstance(row_or_dict, pd.Series):
        data = row_or_dict.to_dict()
    else:
        data = dict(row_or_dict)

    # Check primary condition field
    condition = data.get("condition")
    if condition:
        normalized = normalize_condition(condition)
        if normalized != "unknown":
            return normalized

    # Check condition_detail field
    condition_detail = data.get("condition_detail")
    if condition_detail:
        normalized = normalize_condition(condition_detail)
        if normalized != "unknown":
            return normalized

    # Check notes for condition hints
    notes = data.get("notes")
    if notes:
        # Look for condition keywords in notes
        notes_lower = str(notes).lower()
        if "open box" in notes_lower or "opened" in notes_lower:
            return "open_box"
        if "damaged" in notes_lower or "broken" in notes_lower:
            return "for_parts"
        if "like new" in notes_lower or "mint" in notes_lower:
            return "like_new"
        if "refurb" in notes_lower:
            return "used_good"

    # Check item_condition field
    item_condition = data.get("item_condition")
    if item_condition:
        normalized = normalize_condition(item_condition)
        if normalized != "unknown":
            return normalized

    # Check for grading codes (A, B, C, etc.)
    grade = data.get("grade") or data.get("condition_grade")
    if grade:
        grade_upper = str(grade).upper().strip()
        if grade_upper in ["A", "A+"]:
            return "like_new"
        elif grade_upper in ["B", "B+"]:
            return "used_good"
        elif grade_upper in ["C", "C+"]:
            return "used_fair"
        elif grade_upper in ["D", "F"]:
            return "for_parts"

    # Default to unknown if no condition found
    return "unknown"


def get_condition_stats(df: pd.DataFrame) -> Dict[str, int]:
    """
    Get statistics on condition distribution in a DataFrame.

    Args:
        df: DataFrame with items

    Returns:
        Dictionary with counts per condition bucket
    """
    conditions = df.apply(condition_bucket, axis=1)
    stats = conditions.value_counts().to_dict()

    # Ensure all buckets are represented
    all_buckets = [
        "new",
        "like_new",
        "open_box",
        "used_good",
        "used_fair",
        "for_parts",
        "unknown",
    ]
    for bucket in all_buckets:
        if bucket not in stats:
            stats[bucket] = 0

    return stats
