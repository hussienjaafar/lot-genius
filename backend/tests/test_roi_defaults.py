"""Test that ROI defaults are correctly loaded from config.settings."""

from importlib import reload


def test_roi_defaults_from_settings(monkeypatch):
    """Test ROI defaults reflect config.settings values."""
    # Set custom environment values
    monkeypatch.setenv("MIN_ROI_TARGET", "1.40")
    monkeypatch.setenv("RISK_THRESHOLD", "0.85")
    monkeypatch.setenv("SELLTHROUGH_HORIZON_DAYS", "45")

    # Reload config to pick up new env vars
    from backend.lotgenius import config as cfg

    reload(cfg)

    # Reload roi module to pick up new config values
    from backend.lotgenius import roi as roi_mod

    reload(roi_mod)

    # Verify that DEFAULTS now reflect the environment settings
    assert (
        roi_mod.DEFAULTS["roi_target"] == 1.40
    ), f"Expected roi_target=1.40, got {roi_mod.DEFAULTS['roi_target']}"
    assert (
        roi_mod.DEFAULTS["risk_threshold"] == 0.85
    ), f"Expected risk_threshold=0.85, got {roi_mod.DEFAULTS['risk_threshold']}"
    assert (
        roi_mod.DEFAULTS["horizon_days"] == 45
    ), f"Expected horizon_days=45, got {roi_mod.DEFAULTS['horizon_days']}"


def test_roi_defaults_original_values_preserved():
    """Test that non-overridden defaults remain unchanged."""
    from backend.lotgenius import roi as roi_mod

    # These should remain as original hardcoded values since they're not driven by settings
    assert (
        roi_mod.DEFAULTS["sims"] == 2000
    ), f"Expected sims=2000, got {roi_mod.DEFAULTS['sims']}"
    assert (
        roi_mod.DEFAULTS["salvage_frac"] == 0.50
    ), f"Expected salvage_frac=0.50, got {roi_mod.DEFAULTS['salvage_frac']}"
    assert (
        roi_mod.DEFAULTS["marketplace_fee_pct"] == 0.12
    ), f"Expected marketplace_fee_pct=0.12, got {roi_mod.DEFAULTS['marketplace_fee_pct']}"


def test_roi_defaults_integration_with_settings_object():
    """Test that changes to settings object are reflected in DEFAULTS."""
    from backend.lotgenius import roi as roi_mod
    from backend.lotgenius.config import settings

    # Get current values
    original_roi_target = settings.MIN_ROI_TARGET
    original_risk_threshold = settings.RISK_THRESHOLD
    original_horizon = settings.SELLTHROUGH_HORIZON_DAYS

    # Verify current defaults match settings
    assert roi_mod.DEFAULTS["roi_target"] == original_roi_target
    assert roi_mod.DEFAULTS["risk_threshold"] == original_risk_threshold
    assert roi_mod.DEFAULTS["horizon_days"] == original_horizon
