import json
import os
from pathlib import Path
from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Decision policy (minimum gates; not hard-coded targets)
    MIN_ROI_TARGET: float = Field(1.25, description="Minimum acceptable ROI multiple")
    SELLTHROUGH_HORIZON_DAYS: int = Field(60, description="Horizon in days for gate")
    RISK_THRESHOLD: float = Field(0.80, description="Min probability constraint")
    CASHFLOOR: float = Field(0.0, description="Min expected cash recovered by horizon")
    RECENCY_DECAY_LAMBDA: float = Field(
        0.03, description="Decay per day for comp recency"
    )
    CLEARANCE_VALUE_AT_HORIZON: float = Field(
        0.50, description="Salvage fraction at horizon"
    )

    # Throughput (operations) constraints
    THROUGHPUT_MINS_PER_UNIT: float = Field(
        5.0, description="Estimated ops minutes required per unit"
    )
    THROUGHPUT_CAPACITY_MINS_PER_DAY: float = Field(
        480.0, description="Available ops minutes per day (capacity)"
    )

    # Cashflow timing
    PAYOUT_LAG_DAYS: int = Field(
        14,
        description="Days between sale and cash payout (affects cash_60d calculations)",
    )

    # Brand gating and hazmat policy
    GATED_BRANDS_CSV: str = Field(
        "", description="Comma-separated list of brand names to gate"
    )
    HAZMAT_POLICY: str = Field(
        "review",
        description="Hazmat policy: one of {exclude, review, allow}",
    )
    # Feature flags
    ENABLE_SCRAPERS: bool = Field(False, description="Use low-trust scrapers (opt-in)")

    # External comps scrapers (DISABLED by default for safety/perf in prod)
    ENABLE_EBAY_SCRAPER: bool = Field(
        False, description="Enable eBay sold comps scraper"
    )

    # API Configuration for external data sources
    EBAY_APP_ID: str = Field("", description="eBay Developer App ID for API access")
    EBAY_OAUTH_TOKEN: str = Field(
        "", description="eBay OAuth Access Token (preferred over App ID)"
    )
    EBAY_DEV_ID: str = Field("", description="eBay Developer ID")
    EBAY_CERT_ID: str = Field("", description="eBay Certificate ID")
    FACEBOOK_ACCESS_TOKEN: str = Field(
        "", description="Facebook Graph API Access Token"
    )

    # Enhanced matching configuration
    EXTERNAL_COMPS_MIN_MATCH_SCORE: float = Field(
        0.4, description="Minimum ML match score for external comps"
    )
    EXTERNAL_COMPS_USE_ML_MATCHING: bool = Field(
        True, description="Use ML-enhanced product matching"
    )
    ENABLE_FB_SCRAPER: bool = Field(
        False, description="Enable Facebook Marketplace scraper"
    )
    ENABLE_GOOGLE_SEARCH_ENRICHMENT: bool = Field(
        False,
        description="Enable Google Search for item enrichment (low-trust corroboration)",
    )
    SCRAPER_TOS_ACK: bool = Field(
        False, description="Acknowledge scraper Terms of Service"
    )

    # External comps configuration
    EXTERNAL_COMPS_PRIOR_WEIGHT: float = Field(
        0.25, description="Weight for external comps in triangulation"
    )
    EXTERNAL_COMPS_LOOKBACK_DAYS: int = Field(
        180, description="Days to look back for sold comps"
    )
    EXTERNAL_COMPS_MAX_RESULTS: int = Field(
        40, description="Max comps to retrieve per source"
    )
    EXTERNAL_COMPS_CACHE_TTL_DAYS: int = Field(
        7, description="Cache TTL for external comps in days"
    )

    # Tail-risk alpha for VaR/CVaR (0.20 => 80% VaR)
    VAR_ALPHA: float = Field(
        0.20, description="Tail-risk alpha for VaR/CVaR computation"
    )

    # Survival model configuration
    SURVIVAL_MODEL: str = Field(
        "loglogistic", description="Survival model type: proxy or loglogistic"
    )
    SURVIVAL_ALPHA: float = Field(
        1.0, description="Log-logistic scale parameter (time to 50% survival)"
    )
    SURVIVAL_BETA: float = Field(1.0, description="Log-logistic shape parameter")

    # Condition normalization and pricing factors
    CONDITION_PRICE_FACTOR: Dict[str, float] = Field(
        default_factory=lambda: {
            "new": 1.00,
            "like_new": 0.95,
            "open_box": 0.92,
            "used_good": 0.85,
            "used_fair": 0.75,
            "for_parts": 0.40,
            "unknown": 0.90,
        },
        description="Price multipliers by condition bucket",
    )
    CONDITION_VELOCITY_FACTOR: Dict[str, float] = Field(
        default_factory=lambda: {
            "new": 1.00,
            "like_new": 1.00,
            "open_box": 0.95,
            "used_good": 0.90,
            "used_fair": 0.85,
            "for_parts": 0.50,
            "unknown": 0.90,
        },
        description="Sell-through velocity multipliers by condition bucket",
    )

    # Seasonality configuration
    SEASONALITY_ENABLED: bool = Field(
        True, description="Enable seasonality adjustments"
    )
    SEASONALITY_DEFAULT: float = Field(1.0, description="Default seasonality factor")
    SEASONALITY_FILE: str = Field(
        "backend/lotgenius/data/seasonality.example.json",
        description="Path to seasonality data file",
    )

    # External services (Keepa-only for now)
    KEEPA_API_KEY: str | None = None
    KEEPA_CACHE_TTL_DAYS: int = Field(
        7, description="Cache TTL for Keepa responses in days"
    )

    # Header mapping validation
    HEADER_COVERAGE_MIN: float = Field(
        0.70, description="Minimum header coverage for validation"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


def _load_calibration_overrides() -> Dict:
    """
    Load calibration overrides from file specified by LOTGENIUS_CALIBRATION_OVERRIDES env var.
    Returns dict of overrides to merge into settings, or empty dict if no overrides.

    This is opt-in and safe: no file = no overrides.
    Only supports CONDITION_PRICE_FACTOR overrides for now.
    """
    overrides_path = os.environ.get("LOTGENIUS_CALIBRATION_OVERRIDES")
    if not overrides_path:
        return {}

    try:
        overrides_file = Path(overrides_path)
        if not overrides_file.exists():
            return {}

        with open(overrides_file, "r") as f:
            overrides = json.load(f)

        # Only allow documented override keys for safety
        allowed_keys = {"CONDITION_PRICE_FACTOR"}
        safe_overrides = {}

        for key, value in overrides.items():
            if key in allowed_keys:
                safe_overrides[key] = value

        return safe_overrides

    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        # Silently ignore errors to avoid breaking app startup
        return {}


def _create_settings_with_overrides():
    """Create settings instance and apply calibration overrides if present."""
    settings = Settings()

    # Apply calibration overrides if present
    overrides = _load_calibration_overrides()
    if overrides:
        # Only apply CONDITION_PRICE_FACTOR overrides for now
        if "CONDITION_PRICE_FACTOR" in overrides:
            # Merge override factors into existing factors
            current_factors = dict(settings.CONDITION_PRICE_FACTOR)
            override_factors = overrides["CONDITION_PRICE_FACTOR"]

            # Update with overrides
            current_factors.update(override_factors)

            # Create new settings with updated factors
            settings.CONDITION_PRICE_FACTOR = current_factors

    return settings


settings = _create_settings_with_overrides()

# Export settings for easy import
ENABLE_EBAY_SCRAPER = settings.ENABLE_EBAY_SCRAPER
ENABLE_FB_SCRAPER = settings.ENABLE_FB_SCRAPER
ENABLE_GOOGLE_SEARCH_ENRICHMENT = settings.ENABLE_GOOGLE_SEARCH_ENRICHMENT
SCRAPER_TOS_ACK = settings.SCRAPER_TOS_ACK
EXTERNAL_COMPS_PRIOR_WEIGHT = settings.EXTERNAL_COMPS_PRIOR_WEIGHT
EXTERNAL_COMPS_LOOKBACK_DAYS = settings.EXTERNAL_COMPS_LOOKBACK_DAYS
EXTERNAL_COMPS_MAX_RESULTS = settings.EXTERNAL_COMPS_MAX_RESULTS
EXTERNAL_COMPS_CACHE_TTL_DAYS = settings.EXTERNAL_COMPS_CACHE_TTL_DAYS

# Condition and seasonality settings
CONDITION_PRICE_FACTOR = settings.CONDITION_PRICE_FACTOR
CONDITION_VELOCITY_FACTOR = settings.CONDITION_VELOCITY_FACTOR
SEASONALITY_ENABLED = settings.SEASONALITY_ENABLED
SEASONALITY_DEFAULT = settings.SEASONALITY_DEFAULT
SEASONALITY_FILE = settings.SEASONALITY_FILE
