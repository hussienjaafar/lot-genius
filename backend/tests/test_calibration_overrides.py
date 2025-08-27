"""Tests for calibration overrides functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestCalibrationOverrides:
    """Test calibration overrides loading and application."""

    def test_no_overrides_env_var(self):
        """Test that no overrides are loaded when env var is not set."""
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            # Import config with clean env
            import importlib

            import lotgenius.config

            importlib.reload(lotgenius.config)

            # Should use default values
            from lotgenius.config import settings

            assert settings.CONDITION_PRICE_FACTOR["new"] == 1.00
            assert settings.CONDITION_PRICE_FACTOR["used_good"] == 0.85

    def test_nonexistent_overrides_file(self):
        """Test that nonexistent overrides file is silently ignored."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            nonexistent_path = Path(tmp_dir) / "nonexistent.json"

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(nonexistent_path)}
            ):
                import importlib

                import lotgenius.config

                importlib.reload(lotgenius.config)

                # Should use default values
                from lotgenius.config import settings

                assert settings.CONDITION_PRICE_FACTOR["new"] == 1.00
                assert settings.CONDITION_PRICE_FACTOR["used_good"] == 0.85

    def test_valid_overrides_applied(self):
        """Test that valid overrides are properly applied."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create overrides file
            overrides_path = Path(tmp_dir) / "overrides.json"
            overrides_data = {
                "CONDITION_PRICE_FACTOR": {
                    "new": 0.98,
                    "used_good": 0.82,
                    "like_new": 0.93,
                }
            }

            with open(overrides_path, "w") as f:
                json.dump(overrides_data, f)

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(overrides_path)}
            ):
                import importlib

                import lotgenius.config

                importlib.reload(lotgenius.config)

                from lotgenius.config import settings

                # Check overridden values
                assert settings.CONDITION_PRICE_FACTOR["new"] == 0.98
                assert settings.CONDITION_PRICE_FACTOR["used_good"] == 0.82
                assert settings.CONDITION_PRICE_FACTOR["like_new"] == 0.93

                # Check non-overridden values remain default
                assert settings.CONDITION_PRICE_FACTOR["used_fair"] == 0.75  # default
                assert settings.CONDITION_PRICE_FACTOR["for_parts"] == 0.40  # default

    def test_partial_overrides_merge(self):
        """Test that partial overrides merge with existing values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create overrides file with only some factors
            overrides_path = Path(tmp_dir) / "overrides.json"
            overrides_data = {
                "CONDITION_PRICE_FACTOR": {
                    "new": 0.99,
                    "used_good": 0.88,
                    # Missing other factors - should keep defaults
                }
            }

            with open(overrides_path, "w") as f:
                json.dump(overrides_data, f)

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(overrides_path)}
            ):
                import importlib

                import lotgenius.config

                importlib.reload(lotgenius.config)

                from lotgenius.config import settings

                # Check overridden values
                assert settings.CONDITION_PRICE_FACTOR["new"] == 0.99
                assert settings.CONDITION_PRICE_FACTOR["used_good"] == 0.88

                # Check non-overridden values remain default
                assert settings.CONDITION_PRICE_FACTOR["like_new"] == 0.95  # default
                assert settings.CONDITION_PRICE_FACTOR["open_box"] == 0.92  # default
                assert settings.CONDITION_PRICE_FACTOR["used_fair"] == 0.75  # default

    def test_invalid_json_ignored(self):
        """Test that invalid JSON files are silently ignored."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create invalid JSON file
            overrides_path = Path(tmp_dir) / "invalid.json"
            with open(overrides_path, "w") as f:
                f.write("{ invalid json }")

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(overrides_path)}
            ):
                import importlib

                import lotgenius.config

                importlib.reload(lotgenius.config)

                # Should use default values (ignore invalid file)
                from lotgenius.config import settings

                assert settings.CONDITION_PRICE_FACTOR["new"] == 1.00
                assert settings.CONDITION_PRICE_FACTOR["used_good"] == 0.85

    def test_unsupported_keys_filtered(self):
        """Test that only supported override keys are applied."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create overrides file with supported and unsupported keys
            overrides_path = Path(tmp_dir) / "overrides.json"
            overrides_data = {
                "CONDITION_PRICE_FACTOR": {"new": 0.97},
                "UNSUPPORTED_KEY": {"some": "value"},
                "ANOTHER_UNSUPPORTED": "value",
            }

            with open(overrides_path, "w") as f:
                json.dump(overrides_data, f)

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(overrides_path)}
            ):
                import importlib

                import lotgenius.config

                importlib.reload(lotgenius.config)

                from lotgenius.config import settings

                # Supported key should be applied
                assert settings.CONDITION_PRICE_FACTOR["new"] == 0.97

                # Unsupported keys should not be present in settings
                assert not hasattr(settings, "UNSUPPORTED_KEY")
                assert not hasattr(settings, "ANOTHER_UNSUPPORTED")

    def test_overrides_function_directly(self):
        """Test the overrides loading function directly."""
        from lotgenius.config import _load_calibration_overrides

        # Test with no env var
        with patch.dict(os.environ, {}, clear=True):
            overrides = _load_calibration_overrides()
            assert overrides == {}

        # Test with nonexistent file
        with tempfile.TemporaryDirectory() as tmp_dir:
            nonexistent_path = Path(tmp_dir) / "nonexistent.json"
            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(nonexistent_path)}
            ):
                overrides = _load_calibration_overrides()
                assert overrides == {}

        # Test with valid file
        with tempfile.TemporaryDirectory() as tmp_dir:
            overrides_path = Path(tmp_dir) / "test_overrides.json"
            test_data = {
                "CONDITION_PRICE_FACTOR": {"new": 0.96},
                "UNSUPPORTED_KEY": "value",
            }
            with open(overrides_path, "w") as f:
                json.dump(test_data, f)

            with patch.dict(
                os.environ, {"LOTGENIUS_CALIBRATION_OVERRIDES": str(overrides_path)}
            ):
                overrides = _load_calibration_overrides()
                assert overrides == {"CONDITION_PRICE_FACTOR": {"new": 0.96}}
                assert "UNSUPPORTED_KEY" not in overrides
