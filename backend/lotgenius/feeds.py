"""CSV import and enrichment hooks for user-supplied feeds/watchlists."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ids import extract_ids


class FeedValidationError(Exception):
    """Raised when feed CSV validation fails."""

    def __init__(
        self, message: str, row: Optional[int] = None, column: Optional[str] = None
    ):
        self.message = message
        self.row = row
        self.column = column

        details = []
        if row is not None:
            details.append(f"row {row}")
        if column is not None:
            details.append(f"column '{column}'")

        if details:
            super().__init__(f"{message} ({', '.join(details)})")
        else:
            super().__init__(message)


def normalize_condition(condition: str) -> str:
    """
    Normalize condition string to safe buckets.

    Maps various condition descriptions to standardized values.
    Defaults to 'Used' for ambiguous cases.
    """
    if not isinstance(condition, str):
        return "Used"

    condition_lower = condition.strip().lower()

    # New condition mappings
    if condition_lower in ("new", "brand new", "factory sealed", "unopened", "mint"):
        return "New"

    # Like new condition mappings
    if condition_lower in ("like new", "open box", "excellent", "mint condition"):
        return "Like New"

    # Good condition mappings
    if condition_lower in ("good", "used - good", "very good", "fine"):
        return "Used - Good"

    # Fair condition mappings
    if condition_lower in ("fair", "used - fair", "acceptable", "worn"):
        return "Used - Fair"

    # Poor/damaged condition mappings
    if condition_lower in ("poor", "damaged", "broken", "for parts", "salvage"):
        return "For Parts"

    # Default to Used for anything unrecognized
    return "Used"


def normalize_brand(brand: str) -> str:
    """Normalize brand string - trim and lowercase."""
    if not isinstance(brand, str):
        return ""
    return brand.strip().lower()


def normalize_string_field(value: Any) -> str:
    """Normalize any field to trimmed string."""
    if value is None or value == "":
        return ""
    return str(value).strip()


def normalize_numeric_field(value: Any) -> Optional[float]:
    """Normalize numeric field with safe conversion."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def validate_required_fields(record: Dict[str, str], row_idx: int) -> None:
    """
    Validate that required fields are present and non-empty.

    Required fields:
    - title: Must be present and non-empty
    - At least one ID field: asin, upc, ean, or upc_ean_asin (or legacy brand field)

    Args:
        record: CSV record as dict
        row_idx: Row index for error reporting (1-based)

    Raises:
        FeedValidationError: If validation fails
    """
    # Check title
    title = record.get("title", "").strip()
    if not title:
        raise FeedValidationError(
            "Title is required and cannot be empty", row=row_idx, column="title"
        )

    # Check ID fields - at least one must be present
    id_fields = ["asin", "upc", "ean", "upc_ean_asin", "brand"]
    has_id = False
    for field in id_fields:
        if record.get(field, "").strip():
            has_id = True
            break

    if not has_id:
        raise FeedValidationError(
            f"At least one ID field is required: {', '.join(id_fields)}", row=row_idx
        )


def load_feed_csv(path: str) -> List[Dict[str, Any]]:
    """
    Load and normalize a feed CSV file.

    Required columns: title, and at least one of (brand, asin, upc, ean, upc_ean_asin)
    Optional columns: model, condition, quantity, notes, category, color_size_variant, lot_id

    Args:
        path: Path to CSV file

    Returns:
        List of normalized feed records ready for pipeline processing

    Raises:
        FeedValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file encoding issues
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Feed CSV file not found: {path}")

    # Try UTF-8 first, then Windows-safe fallback
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            with open(path_obj, "r", encoding=encoding, newline="") as f:
                return _process_csv_content(f, str(path_obj))
        except UnicodeDecodeError:
            continue

    # If all encodings fail, raise domain error
    raise FeedValidationError(
        f"Unable to read CSV file with supported encodings: {path}"
    )


def _process_csv_content(file_obj, filename: str) -> List[Dict[str, Any]]:
    """Process CSV content from file object."""
    try:
        # Detect CSV dialect
        sample = file_obj.read(1024)
        file_obj.seek(0)

        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample, delimiters=",;\t")
        except csv.Error:
            # Fall back to default Excel dialect
            dialect = csv.excel

        reader = csv.DictReader(file_obj, dialect=dialect)

        # Validate required columns exist
        required_columns = {"title"}
        id_columns = {"brand", "asin", "upc", "ean", "upc_ean_asin"}

        if not reader.fieldnames:
            raise FeedValidationError("CSV file has no headers")

        fieldnames = set(reader.fieldnames)

        # Check required columns
        missing_required = required_columns - fieldnames
        if missing_required:
            raise FeedValidationError(
                f"Missing required columns: {', '.join(missing_required)}"
            )

        # Check that at least one ID column exists
        if not (fieldnames & id_columns):
            raise FeedValidationError(
                f"At least one ID column required: {', '.join(id_columns)}"
            )

        # Process records
        records = []
        for row_idx, record in enumerate(reader, start=2):  # Start at 2 for header row
            try:
                # Validate required fields for this row
                validate_required_fields(record, row_idx)

                # Normalize the record
                normalized = normalize_record(record)
                records.append(normalized)

            except FeedValidationError:
                raise  # Re-raise with context
            except Exception as e:
                raise FeedValidationError(f"Error processing row: {e}", row=row_idx)

        if not records:
            raise FeedValidationError("CSV file contains no data rows")

        return records

    except csv.Error as e:
        raise FeedValidationError(f"CSV parsing error: {e}")


def normalize_record(record: Dict[str, str]) -> Dict[str, Any]:
    """
    Normalize a single CSV record to pipeline-ready format.

    Args:
        record: Raw CSV record as string dict

    Returns:
        Normalized record dict
    """
    normalized = {}

    # Required fields with normalization
    normalized["title"] = normalize_string_field(record.get("title"))

    # ID fields - will be processed by extract_ids later
    normalized["asin"] = normalize_string_field(record.get("asin"))
    normalized["upc"] = normalize_string_field(record.get("upc"))
    normalized["ean"] = normalize_string_field(record.get("ean"))
    normalized["upc_ean_asin"] = normalize_string_field(record.get("upc_ean_asin"))

    # Brand field (special handling - normalize to lowercase)
    brand_raw = record.get("brand", "")
    normalized["brand"] = normalize_brand(brand_raw) if brand_raw else ""

    # Optional string fields
    normalized["model"] = normalize_string_field(record.get("model"))
    normalized["notes"] = normalize_string_field(record.get("notes"))
    normalized["category"] = normalize_string_field(record.get("category"))
    normalized["color_size_variant"] = normalize_string_field(
        record.get("color_size_variant")
    )
    normalized["lot_id"] = normalize_string_field(record.get("lot_id"))
    normalized["sku_local"] = normalize_string_field(record.get("sku_local"))

    # Condition with safe bucketing
    condition_raw = record.get("condition", "Used")
    normalized["condition"] = normalize_condition(condition_raw)

    # Numeric fields
    normalized["quantity"] = normalize_numeric_field(record.get("quantity")) or 1.0
    normalized["est_cost_per_unit"] = normalize_numeric_field(
        record.get("est_cost_per_unit")
    )
    normalized["msrp"] = normalize_numeric_field(record.get("msrp"))

    # Category hint (alias for category)
    if record.get("category_hint") and not normalized["category"]:
        normalized["category_hint"] = normalize_string_field(
            record.get("category_hint")
        )
    else:
        normalized["category_hint"] = normalized["category"]

    return normalized


def feed_to_pipeline_items(feed_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert normalized feed records to pipeline-ready items.

    This function:
    1. Applies ID extraction and normalization via extract_ids()
    2. Ensures all required pipeline fields are present
    3. Maintains original feed fields as passthrough data

    Args:
        feed_records: List of normalized feed records

    Returns:
        List of pipeline-ready items
    """
    pipeline_items = []

    for record in feed_records:
        # Create pipeline item starting with the normalized record
        item = dict(record)

        # Apply ID extraction and normalization
        ids = extract_ids(record)
        item.update(ids)

        # Ensure required pipeline fields exist with defaults
        pipeline_defaults = {
            "sku_local": item.get("sku_local") or f"FEED_{len(pipeline_items)+1:04d}",
            "quantity": item.get("quantity") or 1.0,
            "condition": item.get("condition") or "Used",
            "category_hint": item.get("category_hint") or item.get("category") or "",
        }

        for key, default_value in pipeline_defaults.items():
            if not item.get(key):
                item[key] = default_value

        pipeline_items.append(item)

    return pipeline_items
