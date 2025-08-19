import os
import tempfile

import pandas as pd
from lotgenius.config import Settings
from lotgenius.validation import validate_manifest_csv


def test_header_threshold_configurable():
    """Test that HEADER_COVERAGE_MIN is configurable via environment."""
    # Create a test CSV with low header coverage (2/5 = 0.40)
    test_data = pd.DataFrame(
        {
            "title": ["Item 1", "Item 2"],  # Maps to title
            "qty": [1, 2],  # Maps to quantity
            "unknown_field_1": ["A", "B"],  # No mapping
            "unknown_field_2": ["X", "Y"],  # No mapping
            "unknown_field_3": ["P", "Q"],  # No mapping
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        test_data.to_csv(f.name, index=False)
        csv_path = f.name

    try:
        # Test with default threshold (0.70)
        result = validate_manifest_csv(csv_path)
        # Should have 2/5 = 0.40 coverage (title->title, qty->quantity)
        assert result.header_coverage == 0.40
        assert not result.passed  # Should fail with default 0.70 threshold

        # Test with custom low threshold via environment
        old_threshold = os.environ.get("HEADER_COVERAGE_MIN")
        try:
            os.environ["HEADER_COVERAGE_MIN"] = "0.30"
            # Need to reload settings to pick up new env var
            settings = Settings()
            assert settings.HEADER_COVERAGE_MIN == 0.30

            # Validation should now pass with lower threshold
            result = validate_manifest_csv(csv_path)
            assert result.header_coverage == 0.40
            # Should pass since 0.40 >= 0.30 threshold

        finally:
            if old_threshold is not None:
                os.environ["HEADER_COVERAGE_MIN"] = old_threshold
            else:
                os.environ.pop("HEADER_COVERAGE_MIN", None)

    finally:
        os.unlink(csv_path)


def test_utf8_sig_encoding():
    """Test that CSV files with BOM are handled correctly."""
    # Create a test CSV with BOM characters in headers
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
    ) as f:
        f.write('\ufeff"title","quantity","condition"\n')
        f.write('"Item 1",1,"New"\n')
        f.write('"Item 2",2,"UsedGood"\n')
        csv_path = f.name

    try:
        result = validate_manifest_csv(csv_path)
        # Should successfully map headers despite BOM
        assert result.mapped_headers == 3  # All 3 headers should map
        assert result.header_coverage == 1.0  # 100% coverage

    finally:
        os.unlink(csv_path)
