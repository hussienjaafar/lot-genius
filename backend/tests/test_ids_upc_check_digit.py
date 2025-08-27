"""
Test cases for UPC check digit validation in lotgenius.ids module.

Covers UPC-A check digit validation and integration with ID extraction.
"""

from lotgenius.ids import extract_ids, validate_upc_check_digit


class TestUpcCheckDigitValidation:
    """Test UPC check digit validation functionality."""

    def test_validate_upc_check_digit_valid_examples(self):
        """Test validation returns True for known valid UPCs."""
        # Known valid UPC examples
        assert validate_upc_check_digit("012345678905") == True  # Common test UPC
        assert validate_upc_check_digit("123456789012") == True  # Another test UPC
        assert (
            validate_upc_check_digit("036000291452") == True
        )  # Coca-Cola Classic 12oz Can

    def test_validate_upc_check_digit_invalid_last_digit(self):
        """Test validation returns False for UPC with invalid check digit."""
        assert validate_upc_check_digit("012345678901") == False  # Should be 5, not 1

    def test_validate_upc_check_digit_invalid_formats(self):
        """Test validation handles invalid input formats."""
        assert validate_upc_check_digit("") == False
        assert validate_upc_check_digit("12345") == False  # Too short
        assert validate_upc_check_digit("1234567890123") == False  # Too long
        assert validate_upc_check_digit("12345678901a") == False  # Contains letter
        assert validate_upc_check_digit(None) == False
        assert validate_upc_check_digit(123456789012) == False  # Not a string

    def test_extract_ids_rejects_invalid_upc_in_upc_field(self):
        """Test extract_ids rejects invalid UPC in upc field."""
        item = {"upc": "012345678901"}  # Invalid check digit
        result = extract_ids(item)

        assert result["upc"] is None  # Should not be classified as UPC
        assert result["upc_ean_asin"] is None  # No valid UPC found
        assert result["ean"] is None
        assert result["asin"] is None

    def test_extract_ids_rejects_invalid_upc_in_canonical(self):
        """Test extract_ids rejects invalid UPC in upc_ean_asin field."""
        item = {"upc_ean_asin": "012345678901"}  # Invalid check digit
        result = extract_ids(item)

        assert result["upc"] is None  # Should not be classified as UPC
        assert result["upc_ean_asin"] == "012345678901"  # Canonical field preserved
        assert result["ean"] is None  # Not 13 digits
        assert result["asin"] is None  # Not ASIN format

    def test_extract_ids_accepts_valid_upc(self):
        """Test extract_ids accepts valid UPC and sets canonical."""
        item = {"upc": "012345678905"}  # Valid check digit
        result = extract_ids(item)

        assert result["upc"] == "012345678905"  # Valid UPC accepted
        assert result["upc_ean_asin"] == "012345678905"  # Canonical matches
        assert result["ean"] is None
        assert result["asin"] is None

    def test_extract_ids_valid_upc_in_canonical(self):
        """Test extract_ids accepts valid UPC in upc_ean_asin field."""
        item = {"upc_ean_asin": "012345678905"}  # Valid check digit
        result = extract_ids(item)

        assert result["upc"] == "012345678905"  # Classified as UPC
        assert result["upc_ean_asin"] == "012345678905"  # Canonical preserved
        assert result["ean"] is None
        assert result["asin"] is None

    def test_ean_13_behavior_unchanged(self):
        """Test EAN-13 behavior is not affected by UPC validation."""
        item = {"ean": "4006381333931"}  # 13-digit EAN
        result = extract_ids(item)

        assert result["ean"] == "4006381333931"  # EAN accepted
        assert result["upc_ean_asin"] == "4006381333931"  # Canonical matches
        assert result["upc"] is None
        assert result["asin"] is None

    def test_asin_behavior_unchanged(self):
        """Test ASIN behavior is not affected by UPC validation."""
        item = {"asin": "B012345678"}
        result = extract_ids(item)

        assert result["asin"] == "B012345678"  # ASIN accepted
        assert result["upc_ean_asin"] is None  # ASIN doesn't populate canonical
        assert result["upc"] is None
        assert result["ean"] is None

    def test_mixed_valid_and_invalid_upcs(self):
        """Test precedence with mix of valid and invalid UPCs."""
        # Invalid UPC in canonical, valid UPC in separate field
        item = {
            "upc_ean_asin": "012345678901",  # Invalid check digit
            "upc": "012345678905",  # Valid check digit
        }
        result = extract_ids(item)

        # Canonical takes priority but doesn't classify as UPC due to invalid check digit
        assert result["upc"] is None  # Invalid canonical UPC not classified
        assert result["upc_ean_asin"] == "012345678901"  # Canonical preserved
        assert result["ean"] is None
        assert result["asin"] is None
