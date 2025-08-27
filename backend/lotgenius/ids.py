from __future__ import annotations

import re
from typing import Dict, Optional


def normalize_digits(s: Optional[str]) -> Optional[str]:
    """Extract digits from string, return None if no digits found."""
    if not isinstance(s, str):
        return None
    d = re.sub(r"[^0-9]", "", s)
    return d or None


def normalize_asin(s: Optional[str]) -> Optional[str]:
    """Normalize ASIN to uppercase, validate 10-char alphanumeric format."""
    if not isinstance(s, str):
        return None
    t = s.strip().upper()
    return t if (len(t) == 10 and t.isalnum()) else None


def validate_upc_check_digit(upc: str) -> bool:
    """
    Validate UPC-A check digit using modulo-10 algorithm.

    Args:
        upc: String containing exactly 12 digits

    Returns:
        True if check digit is valid, False otherwise
    """
    if not isinstance(upc, str) or len(upc) != 12 or not upc.isdigit():
        return False

    # Calculate check digit using UPC-A algorithm
    # Odd positions (1st, 3rd, 5th, 7th, 9th, 11th) - indices 0,2,4,6,8,10
    odd_sum = sum(int(upc[i]) for i in [0, 2, 4, 6, 8, 10])

    # Even positions (2nd, 4th, 6th, 8th, 10th) - indices 1,3,5,7,9
    even_sum = sum(int(upc[i]) for i in [1, 3, 5, 7, 9])

    # Calculate expected check digit
    check = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10

    # Compare with actual check digit (12th digit, index 11)
    return int(upc[11]) == check


def extract_ids(item: Dict) -> Dict[str, Optional[str]]:
    """
    Extract and normalize product identifiers from input item.

    Logic:
    1. upc_ean_asin takes priority and gets classified by digit count
    2. If no upc_ean_asin, use upc > ean precedence for canonical
    3. ASIN is handled separately and doesn't affect canonical upc_ean_asin
    4. 12 digits = UPC, 13 digits = EAN

    Args:
        item: Input dictionary containing product data

    Returns:
        Dictionary with normalized ID fields
    """
    # Extract and normalize ASIN (always separate)
    asin = normalize_asin(item.get("asin"))

    # Initialize result fields
    result_upc = None
    result_ean = None
    result_canonical = None

    # Process upc_ean_asin field first (highest priority)
    canonical_raw = item.get("upc_ean_asin", "")
    if canonical_raw:
        # First check if it's a valid ASIN
        canonical_asin = normalize_asin(canonical_raw)
        if canonical_asin:
            result_canonical = canonical_asin
        else:
            # Try as digits for UPC/EAN
            canonical_digits = normalize_digits(canonical_raw)
            if canonical_digits:
                result_canonical = canonical_digits
                # Classify by digit count with UPC validation
                if len(canonical_digits) == 12:
                    if validate_upc_check_digit(canonical_digits):
                        result_upc = canonical_digits
                elif len(canonical_digits) == 13:
                    result_ean = canonical_digits

    # If no upc_ean_asin, process separate fields with upc > ean precedence
    if not result_canonical:
        # Try UPC field
        upc_raw = item.get("upc", "")
        if upc_raw:
            upc_digits = normalize_digits(upc_raw)
            if (
                upc_digits
                and len(upc_digits) == 12
                and validate_upc_check_digit(upc_digits)
            ):
                result_upc = upc_digits
                result_canonical = upc_digits

        # Try EAN field only if no UPC found
        if not result_canonical:
            ean_raw = item.get("ean", "")
            if ean_raw:
                ean_digits = normalize_digits(ean_raw)
                if ean_digits and len(ean_digits) == 13:
                    result_ean = ean_digits
                    result_canonical = ean_digits

    return {
        "asin": asin,
        "upc": result_upc,
        "ean": result_ean,
        "upc_ean_asin": result_canonical,
    }
