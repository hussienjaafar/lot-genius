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

    # Feature flags
    ENABLE_SCRAPERS: bool = Field(False, description="Use low-trust scrapers (opt-in)")

    # External comps scrapers (disabled by default, require ToS acknowledgment)
    ENABLE_EBAY_SCRAPER: bool = Field(
        False, description="Enable eBay sold comps scraper"
    )
    ENABLE_FB_SCRAPER: bool = Field(
        False, description="Enable Facebook Marketplace scraper"
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

    # Tail-risk alpha for VaR/CVaR (0.20 => 80% VaR)
    VAR_ALPHA: float = Field(
        0.20, description="Tail-risk alpha for VaR/CVaR computation"
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


settings = Settings()

# Export settings for easy import
ENABLE_EBAY_SCRAPER = settings.ENABLE_EBAY_SCRAPER
ENABLE_FB_SCRAPER = settings.ENABLE_FB_SCRAPER
SCRAPER_TOS_ACK = settings.SCRAPER_TOS_ACK
EXTERNAL_COMPS_PRIOR_WEIGHT = settings.EXTERNAL_COMPS_PRIOR_WEIGHT
EXTERNAL_COMPS_LOOKBACK_DAYS = settings.EXTERNAL_COMPS_LOOKBACK_DAYS
EXTERNAL_COMPS_MAX_RESULTS = settings.EXTERNAL_COMPS_MAX_RESULTS
