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

    # External services (Keepa-only for now)
    KEEPA_KEY: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
