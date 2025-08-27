"""
Test cases for ID extraction from lotgenius.ids module.

Covers various input formats and edge cases for UPC/EAN/ASIN extraction.
"""

from lotgenius.ids import extract_ids


class TestExtractIds:
    """Test ID extraction from various input formats."""

    def test_case_a_upc_ean_asin_only(self):
        """Case A: Input with only upc_ean_asin field."""
        item = {"upc_ean_asin": "012345678905"}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"
        assert result["upc"] == "012345678905"  # 12 digits -> UPC
        assert result["ean"] is None  # not 13 digits
        assert result["asin"] is None  # not ASIN format

    def test_case_b_asin_only(self):
        """Case B: Input with only asin field."""
        item = {"asin": "B012345678"}
        result = extract_ids(item)

        assert result["asin"] == "B012345678"
        assert (
            result["upc_ean_asin"] is None
        )  # no candidate from upc_ean_asin/upc/ean fields
        assert result["upc"] is None
        assert result["ean"] is None

    def test_case_c_upc_field(self):
        """Case C: Input with upc field."""
        item = {"upc": "012345678905"}
        result = extract_ids(item)

        assert result["upc"] == "012345678905"
        assert result["upc_ean_asin"] == "012345678905"  # canonical
        assert result["ean"] is None
        assert result["asin"] is None

    def test_case_d_ean_field(self):
        """Case D: Input with ean field (13 digits)."""
        item = {"ean": "4006381333931"}
        result = extract_ids(item)

        assert result["ean"] == "4006381333931"
        assert result["upc_ean_asin"] == "4006381333931"  # canonical
        assert result["upc"] is None  # not 12 digits
        assert result["asin"] is None

    def test_case_e_mixed_punctuation(self):
        """Case E: Input with mixed punctuation that needs normalization."""
        item = {"upc_ean_asin": "0-123-456-789-05"}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"  # normalized
        assert result["upc"] == "012345678905"
        assert result["ean"] is None
        assert result["asin"] is None

    def test_priority_order_upc_ean_asin_wins(self):
        """upc_ean_asin takes priority over upc/ean fields."""
        item = {
            "upc_ean_asin": "012345678905",
            "upc": "999888777666",
            "ean": "4006381333931",
        }
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"  # priority field wins
        assert result["upc"] == "012345678905"  # based on canonical
        assert result["ean"] is None  # not 13 digits

    def test_priority_order_upc_over_ean(self):
        """upc takes priority over ean when no upc_ean_asin."""
        item = {"upc": "012345678905", "ean": "4006381333931"}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"  # upc wins
        assert result["upc"] == "012345678905"
        assert result["ean"] is None  # didn't use ean field

    def test_asin_with_other_fields(self):
        """ASIN in separate field with numeric IDs present."""
        item = {"asin": "B012345678", "upc": "012345678905"}
        result = extract_ids(item)

        assert result["asin"] == "B012345678"
        assert (
            result["upc_ean_asin"] == "012345678905"
        )  # upc takes priority for canonical
        assert result["upc"] == "012345678905"
        assert result["ean"] is None

    def test_empty_fields(self):
        """Empty or None values in ID fields."""
        item = {"upc_ean_asin": "", "upc": None, "ean": "", "asin": None}
        result = extract_ids(item)

        assert result["upc_ean_asin"] is None
        assert result["upc"] is None
        assert result["ean"] is None
        assert result["asin"] is None

    def test_invalid_formats(self):
        """Invalid formats that don't match expected patterns."""
        item = {"upc_ean_asin": "invalid123"}
        result = extract_ids(item)

        assert (
            result["upc_ean_asin"] == "INVALID123"
        )  # valid ASIN format (10 alphanumeric)
        assert result["upc"] is None  # not valid UPC format (not 12 digits)
        assert result["ean"] is None  # not valid EAN format (not 13 digits)
        assert result["asin"] is None

    def test_whitespace_normalization(self):
        """Whitespace in ID fields gets normalized."""
        item = {"upc_ean_asin": "  012345678905  "}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"
        assert result["upc"] == "012345678905"
        assert result["ean"] is None
        assert result["asin"] is None

    def test_asin_normalization(self):
        """ASIN normalization handles various formats."""
        item = {"asin": "  b012345678  "}  # lowercase, whitespace
        result = extract_ids(item)

        assert result["asin"] == "B012345678"  # normalized to uppercase
        assert (
            result["upc_ean_asin"] is None
        )  # no candidate from upc_ean_asin/upc/ean fields
        assert result["upc"] is None
        assert result["ean"] is None

    def test_missing_all_fields(self):
        """Item with no ID fields at all."""
        item = {"title": "Some product", "price": 29.99}
        result = extract_ids(item)

        assert result["upc_ean_asin"] is None
        assert result["upc"] is None
        assert result["ean"] is None
        assert result["asin"] is None

    def test_ean_13_digit_detection(self):
        """13-digit codes correctly identified as EAN."""
        item = {"upc_ean_asin": "1234567890123"}  # 13 digits
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "1234567890123"
        assert result["ean"] == "1234567890123"  # 13 digits -> EAN
        assert result["upc"] is None  # not 12 digits
        assert result["asin"] is None

    def test_upc_12_digit_detection(self):
        """12-digit codes correctly identified as UPC."""
        item = {"upc_ean_asin": "123456789012"}  # 12 digits
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "123456789012"
        assert result["upc"] == "123456789012"  # 12 digits -> UPC
        assert result["ean"] is None  # not 13 digits
        assert result["asin"] is None

    def test_complex_punctuation_removal(self):
        """Complex punctuation patterns get normalized."""
        item = {"upc_ean_asin": "0-12.345 678/905"}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "012345678905"
        assert result["upc"] == "012345678905"
        assert result["ean"] is None
        assert result["asin"] is None

    def test_asin_in_upc_ean_asin_field(self):
        """ASIN provided in upc_ean_asin field gets normalized properly."""
        item = {"upc_ean_asin": "B012345678"}
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "B012345678"  # canonical ASIN
        assert result["asin"] is None  # from separate asin field
        assert result["upc"] is None
        assert result["ean"] is None

    def test_truly_invalid_formats(self):
        """Formats that don't match ASIN or digit patterns."""
        item = {"upc_ean_asin": "toolong12345"}  # 11 chars, invalid ASIN
        result = extract_ids(item)

        assert result["upc_ean_asin"] == "12345"  # falls back to digits only
        assert result["upc"] is None  # not 12 digits
        assert result["ean"] is None  # not 13 digits
        assert result["asin"] is None
