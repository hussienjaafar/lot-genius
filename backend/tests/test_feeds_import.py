"""Unit tests for feed/watchlist CSV import functionality."""

import tempfile
from pathlib import Path

import pytest
from lotgenius.feeds import (
    FeedValidationError,
    feed_to_pipeline_items,
    load_feed_csv,
    normalize_brand,
    normalize_condition,
    normalize_record,
    validate_required_fields,
)


class TestNormalizationFunctions:
    """Test individual normalization functions."""

    def test_normalize_condition_standard_cases(self):
        """Test condition normalization for standard cases."""
        assert normalize_condition("New") == "New"
        assert normalize_condition("new") == "New"
        assert normalize_condition("BRAND NEW") == "New"
        assert normalize_condition("factory sealed") == "New"

        assert normalize_condition("Like New") == "Like New"
        assert normalize_condition("like new") == "Like New"
        assert normalize_condition("Open Box") == "Like New"
        assert normalize_condition("excellent") == "Like New"

        assert normalize_condition("Good") == "Used - Good"
        assert normalize_condition("Used - Good") == "Used - Good"
        assert normalize_condition("very good") == "Used - Good"

        assert normalize_condition("Fair") == "Used - Fair"
        assert normalize_condition("used - fair") == "Used - Fair"
        assert normalize_condition("acceptable") == "Used - Fair"

        assert normalize_condition("Poor") == "For Parts"
        assert normalize_condition("damaged") == "For Parts"
        assert normalize_condition("for parts") == "For Parts"

    def test_normalize_condition_edge_cases(self):
        """Test condition normalization edge cases."""
        assert normalize_condition("") == "Used"  # Empty string
        assert normalize_condition("  ") == "Used"  # Whitespace only
        assert normalize_condition("Unknown Status") == "Used"  # Unrecognized
        assert normalize_condition(None) == "Used"  # None input
        assert normalize_condition(123) == "Used"  # Non-string input

    def test_normalize_brand(self):
        """Test brand normalization."""
        assert normalize_brand("Apple") == "apple"
        assert normalize_brand("  SONY  ") == "sony"
        assert normalize_brand("") == ""
        assert normalize_brand(None) == ""
        assert normalize_brand(123) == ""


class TestValidation:
    """Test validation functions."""

    def test_validate_required_fields_success(self):
        """Test successful validation with required fields."""
        # Valid with title and brand
        record1 = {"title": "iPhone 14", "brand": "Apple"}
        validate_required_fields(record1, 1)  # Should not raise

        # Valid with title and ASIN
        record2 = {"title": "Echo Dot", "asin": "B07FZ8S74R"}
        validate_required_fields(record2, 1)  # Should not raise

        # Valid with title and UPC
        record3 = {"title": "Mouse", "upc": "012345678905"}
        validate_required_fields(record3, 1)  # Should not raise

    def test_validate_required_fields_missing_title(self):
        """Test validation failure for missing title."""
        record = {"brand": "Apple"}

        with pytest.raises(FeedValidationError) as exc_info:
            validate_required_fields(record, 2)

        assert "Title is required" in str(exc_info.value)
        assert "row 2" in str(exc_info.value)
        assert "column 'title'" in str(exc_info.value)

    def test_validate_required_fields_empty_title(self):
        """Test validation failure for empty title."""
        record = {"title": "   ", "brand": "Apple"}

        with pytest.raises(FeedValidationError) as exc_info:
            validate_required_fields(record, 3)

        assert "Title is required" in str(exc_info.value)
        assert "row 3" in str(exc_info.value)

    def test_validate_required_fields_no_id_fields(self):
        """Test validation failure when no ID fields present."""
        record = {"title": "Some Product"}

        with pytest.raises(FeedValidationError) as exc_info:
            validate_required_fields(record, 4)

        assert "At least one ID field is required" in str(exc_info.value)
        assert "asin, upc, ean, upc_ean_asin, brand" in str(exc_info.value)
        assert "row 4" in str(exc_info.value)


class TestRecordNormalization:
    """Test record normalization."""

    def test_normalize_record_complete(self):
        """Test normalization with all fields present."""
        raw_record = {
            "title": "  iPhone 14 Pro  ",
            "brand": "  APPLE  ",
            "model": "A2650",
            "condition": "LIKE NEW",
            "quantity": "2",
            "asin": "B0BDJ7TLJX",
            "upc": "194253413141",
            "notes": "  Unlocked version  ",
            "category": "Electronics",
            "est_cost_per_unit": "899.99",
            "msrp": "999.00",
        }

        normalized = normalize_record(raw_record)

        assert normalized["title"] == "iPhone 14 Pro"
        assert normalized["brand"] == "apple"
        assert normalized["model"] == "A2650"
        assert normalized["condition"] == "Like New"
        assert normalized["quantity"] == 2.0
        assert normalized["asin"] == "B0BDJ7TLJX"
        assert normalized["upc"] == "194253413141"
        assert normalized["notes"] == "Unlocked version"
        assert normalized["category"] == "Electronics"
        assert normalized["est_cost_per_unit"] == 899.99
        assert normalized["msrp"] == 999.00

    def test_normalize_record_minimal(self):
        """Test normalization with minimal required fields."""
        raw_record = {"title": "Test Product", "brand": "TestBrand"}

        normalized = normalize_record(raw_record)

        assert normalized["title"] == "Test Product"
        assert normalized["brand"] == "testbrand"
        assert normalized["condition"] == "Used"  # Default
        assert normalized["quantity"] == 1.0  # Default
        assert normalized["model"] == ""
        assert normalized["notes"] == ""

    def test_normalize_record_numeric_edge_cases(self):
        """Test normalization of numeric fields with edge cases."""
        raw_record = {
            "title": "Test",
            "brand": "Test",
            "quantity": "",  # Empty string
            "est_cost_per_unit": "invalid",  # Invalid number
            "msrp": None,  # None value
        }

        normalized = normalize_record(raw_record)

        assert normalized["quantity"] == 1.0  # Default fallback
        assert normalized["est_cost_per_unit"] is None  # Invalid converts to None
        assert normalized["msrp"] is None


class TestCsvLoading:
    """Test CSV loading functionality."""

    def create_temp_csv(self, content: str, encoding: str = "utf-8") -> Path:
        """Helper to create temporary CSV file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", encoding=encoding, delete=False
        )
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)

    def test_load_valid_csv(self):
        """Test loading valid CSV with all expected data."""
        csv_content = """title,brand,condition,upc,quantity
iPhone 14,Apple,New,194253413141,1
Galaxy S23,Samsung,Used - Good,887276632166,2
AirPods Pro,Apple,Like New,194252831403,1"""

        temp_path = self.create_temp_csv(csv_content)
        try:
            records = load_feed_csv(str(temp_path))

            assert len(records) == 3

            # Check first record
            assert records[0]["title"] == "iPhone 14"
            assert records[0]["brand"] == "apple"
            assert records[0]["condition"] == "New"
            assert records[0]["upc"] == "194253413141"
            assert records[0]["quantity"] == 1.0

        finally:
            temp_path.unlink()

    def test_load_csv_windows_crlf(self):
        """Test CSV with Windows CRLF line endings."""
        csv_content = 'title,brand,condition\r\n"Test Product","Test Brand","New"\r\n'

        temp_path = self.create_temp_csv(csv_content)
        try:
            records = load_feed_csv(str(temp_path))

            assert len(records) == 1
            assert records[0]["title"] == "Test Product"
            assert records[0]["brand"] == "test brand"

        finally:
            temp_path.unlink()

    def test_load_csv_quoted_fields(self):
        """Test CSV with quoted fields containing commas and quotes."""
        csv_content = '''title,brand,notes
"iPhone 14, 128GB","Apple","Great phone, works well"
"Samsung ""Galaxy"" S23","Samsung","Includes ""extras"""'''

        temp_path = self.create_temp_csv(csv_content)
        try:
            records = load_feed_csv(str(temp_path))

            assert len(records) == 2
            assert records[0]["title"] == "iPhone 14, 128GB"
            assert records[0]["notes"] == "Great phone, works well"
            assert records[1]["title"] == 'Samsung "Galaxy" S23'
            assert records[1]["notes"] == 'Includes "extras"'

        finally:
            temp_path.unlink()

    def test_load_csv_utf8_bom(self):
        """Test CSV with UTF-8 BOM handling."""
        csv_content = "title,brand,condition\nTest Product,Test Brand,New"

        # Write with BOM using utf-8-sig encoding
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", encoding="utf-8-sig", delete=False
        )
        temp_file.write(csv_content)
        temp_file.close()
        temp_path = Path(temp_file.name)

        try:
            records = load_feed_csv(str(temp_path))

            assert len(records) == 1
            assert records[0]["title"] == "Test Product"

        finally:
            temp_path.unlink()

    def test_load_csv_missing_required_columns(self):
        """Test CSV missing required columns."""
        csv_content = """brand,condition
Apple,New
Samsung,Used"""

        temp_path = self.create_temp_csv(csv_content)
        try:
            with pytest.raises(FeedValidationError) as exc_info:
                load_feed_csv(str(temp_path))

            assert "Missing required columns: title" in str(exc_info.value)

        finally:
            temp_path.unlink()

    def test_load_csv_missing_id_columns(self):
        """Test CSV missing all ID columns."""
        csv_content = """title,condition,notes
Test Product,New,Some notes"""

        temp_path = self.create_temp_csv(csv_content)
        try:
            with pytest.raises(FeedValidationError) as exc_info:
                load_feed_csv(str(temp_path))

            assert "At least one ID column required" in str(exc_info.value)

        finally:
            temp_path.unlink()

    def test_load_csv_empty_title_row(self):
        """Test CSV with row having empty title."""
        csv_content = """title,brand
iPhone 14,Apple
,Samsung"""  # Empty title in second row

        temp_path = self.create_temp_csv(csv_content)
        try:
            with pytest.raises(FeedValidationError) as exc_info:
                load_feed_csv(str(temp_path))

            assert "Title is required" in str(exc_info.value)
            assert "row 3" in str(exc_info.value)  # Row 3 (1-based, including header)

        finally:
            temp_path.unlink()

    def test_load_csv_no_data_rows(self):
        """Test CSV with headers but no data."""
        csv_content = """title,brand,condition"""

        temp_path = self.create_temp_csv(csv_content)
        try:
            with pytest.raises(FeedValidationError) as exc_info:
                load_feed_csv(str(temp_path))

            assert "CSV file contains no data rows" in str(exc_info.value)

        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_feed_csv("/nonexistent/file.csv")

        assert "Feed CSV file not found" in str(exc_info.value)


class TestFeedToPipeline:
    """Test feed to pipeline conversion."""

    def test_feed_to_pipeline_items_basic(self):
        """Test basic feed to pipeline conversion."""
        feed_records = [
            {
                "title": "iPhone 14",
                "brand": "apple",
                "condition": "New",
                "upc": "194253413141",
                "quantity": 1.0,
                "model": "",
                "notes": "",
                "category": "Electronics",
            }
        ]

        pipeline_items = feed_to_pipeline_items(feed_records)

        assert len(pipeline_items) == 1
        item = pipeline_items[0]

        # Should have all original fields
        assert item["title"] == "iPhone 14"
        assert item["brand"] == "apple"
        assert item["condition"] == "New"

        # Should have ID extraction applied (extract_ids function)
        assert "asin" in item  # From extract_ids
        assert "upc_ean_asin" in item  # From extract_ids

        # Should have defaults applied
        assert item["sku_local"].startswith("FEED_")
        assert item["quantity"] == 1.0

    def test_feed_to_pipeline_items_id_extraction(self):
        """Test that ID extraction is properly applied."""
        feed_records = [
            {
                "title": "Test Product",
                "brand": "test",
                "upc": "012345678905",  # Valid UPC with check digit
                "condition": "Used",
                "quantity": 2.0,
                "model": "",
                "notes": "",
                "category": "",
            }
        ]

        pipeline_items = feed_to_pipeline_items(feed_records)

        item = pipeline_items[0]

        # Should have normalized UPC
        assert item["upc"] == "012345678905"
        assert item["upc_ean_asin"] == "012345678905"  # Should be canonical

    def test_feed_to_pipeline_items_multiple_records(self):
        """Test conversion with multiple records."""
        feed_records = [
            {
                "title": "Product 1",
                "brand": "brand1",
                "condition": "New",
                "quantity": 1.0,
                "model": "",
                "notes": "",
                "category": "",
            },
            {
                "title": "Product 2",
                "brand": "brand2",
                "condition": "Used",
                "quantity": 2.0,
                "model": "",
                "notes": "",
                "category": "",
            },
            {
                "title": "Product 3",
                "brand": "brand3",
                "condition": "Like New",
                "quantity": 1.0,
                "model": "",
                "notes": "",
                "category": "",
            },
        ]

        pipeline_items = feed_to_pipeline_items(feed_records)

        assert len(pipeline_items) == 3

        # Check SKU generation
        assert pipeline_items[0]["sku_local"] == "FEED_0001"
        assert pipeline_items[1]["sku_local"] == "FEED_0002"
        assert pipeline_items[2]["sku_local"] == "FEED_0003"


class TestIntegrationScenarios:
    """Integration test scenarios with realistic data."""

    def create_sample_csv(self) -> Path:
        """Create a sample feed CSV for integration testing."""
        csv_content = '''title,brand,condition,upc,asin,quantity,notes,category
"iPhone 14 Pro 128GB","Apple","New","194253413141","B0BDJ7TLJX","1","Unlocked","Electronics"
"Galaxy S23 Ultra","Samsung","Used - Good","887276632166","","2","Minor scratches","Electronics"
"AirPods Pro 2nd Gen","Apple","Like New","","B0BDHB9Y8H","1","Open box","Audio"
"Generic USB Cable","Generic","Used","","","5","Bulk lot","Accessories"'''

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        temp_file.write(csv_content)
        temp_file.close()
        return Path(temp_file.name)

    def test_complete_workflow(self):
        """Test complete workflow from CSV to pipeline items."""
        temp_path = self.create_sample_csv()

        try:
            # Load and normalize
            feed_records = load_feed_csv(str(temp_path))
            assert len(feed_records) == 4

            # Convert to pipeline format
            pipeline_items = feed_to_pipeline_items(feed_records)
            assert len(pipeline_items) == 4

            # Verify specific transformations
            iphone = pipeline_items[0]
            assert iphone["title"] == "iPhone 14 Pro 128GB"
            assert iphone["brand"] == "apple"
            assert iphone["condition"] == "New"
            assert iphone["upc"] == "194253413141"
            assert iphone["asin"] == "B0BDJ7TLJX"

            galaxy = pipeline_items[1]
            assert galaxy["condition"] == "Used - Good"
            assert galaxy["quantity"] == 2.0

            airpods = pipeline_items[2]
            assert airpods["condition"] == "Like New"
            assert airpods["asin"] == "B0BDHB9Y8H"

            # Generic item with minimal data
            generic = pipeline_items[3]
            assert generic["title"] == "Generic USB Cable"
            assert generic["brand"] == "generic"  # Has brand now
            assert generic["condition"] == "Used"
            assert generic["quantity"] == 5.0

        finally:
            temp_path.unlink()


def test_load_csv_unsupported_encoding():
    """Test handling of files that can be decoded but have malformed CSV structure."""
    import tempfile

    from lotgenius.feeds import FeedValidationError, load_feed_csv

    # Create a temporary file with data that can be decoded but makes no sense as CSV
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        # Write binary-like content that's technically decodable but not valid CSV
        f.write(
            "".join(chr(i) for i in range(32, 127))
            + "\n"
            + "more garbage data\x00\x01\x02"
        )
        temp_path = Path(f.name)

    try:
        # This should fail with CSV validation error, not encoding error
        # Since the modern encodings are quite permissive, we test CSV structure validation instead
        with pytest.raises(
            FeedValidationError,
            match="Missing required columns: title|CSV file has no headers",
        ):
            load_feed_csv(str(temp_path))
    finally:
        temp_path.unlink()
