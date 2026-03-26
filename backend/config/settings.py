"""
config/settings.py — GigKavach Configuration
─────────────────────────────────────────────
Loads all environment variables from .env and exposes them as typed
settings throughout the application.

Usage anywhere in the codebase:
    from config.settings import settings
    print(settings.SUPABASE_URL)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Pydantic Settings model — reads from environment / .env file automatically.
    All values here correspond to keys in .env.example.
    """

    # ── Model config: tells Pydantic to read from .env file ──────────
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env in the project root
        env_file_encoding="utf-8",
        case_sensitive=True,       # env var names are case-sensitive
        extra="ignore",            # Silently ignore unknown env vars
    )

    # ── App ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production"

    # ── Supabase ──────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── Cache ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Twilio ───────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"
    TWILIO_SMS_NUMBER: str = ""

    # ── Razorpay ─────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Weather APIs ─────────────────────────────────────────────────
    TOMORROW_IO_API_KEY: str = ""

    # ── AQI APIs ─────────────────────────────────────────────────────
    AQICN_API_TOKEN: str = ""
    OPENAQ_API_KEY: str = ""

    # ── Geocoding ────────────────────────────────────────────────────
    MAPPLS_API_KEY: str = ""

    # ── DCI Engine Config ────────────────────────────────────────────
    DCI_POLL_INTERVAL_SECONDS: int = 300       # 5 minutes between DCI recalculations
    DCI_TRIGGER_THRESHOLD: int = 65            # DCI >= 65 → payout evaluation starts
    DCI_CATASTROPHIC_THRESHOLD: int = 85       # DCI >= 85 → catastrophic, no login needed
    DCI_CACHE_TTL_SECONDS: int = 1800          # 30 min cache → SLA breach if exceeded

    # ── Fraud Detection Config ────────────────────────────────────────
    FRAUD_SOFT_FLAG_SIGNALS: int = 3           # Tier 1: 50% payout + 48hr re-verify
    FRAUD_HARD_BLOCK_SIGNALS: int = 5          # Tier 2: full block
    FRAUD_CONTAMINATION_RATE: float = 0.05     # Isolation Forest param (5% assumed fraud)

    # ── Payout Config ─────────────────────────────────────────────────
    COVERAGE_DELAY_HOURS: int = 24             # New workers wait 24hrs before coverage
    MAX_UPI_RETRY_ATTEMPTS: int = 3            # Razorpay retry attempts before escrow
    UPI_RETRY_INTERVAL_MINUTES: int = 40       # Minutes between UPI retries
    ESCROW_WINDOW_HOURS: int = 48              # Worker correction window before lapse

    # ── Premium Tiers (in INR) ────────────────────────────────────────
    # Fixed weekly premiums — workers choose at onboarding, cannot change mid-week
    SHIELD_BASIC_PREMIUM: int = 69             # 40% of daily earnings covered
    SHIELD_PLUS_PREMIUM: int = 89              # 50% of daily earnings covered
    SHIELD_PRO_PREMIUM: int = 99               # 70% of daily earnings covered

    SHIELD_BASIC_COVERAGE_PCT: float = 0.40
    SHIELD_PLUS_COVERAGE_PCT: float = 0.50
    SHIELD_PRO_COVERAGE_PCT: float = 0.70


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton of the Settings object.
    Using lru_cache means .env is read exactly once at startup,
    not on every settings access.
    """
    return Settings()


# Convenience — import this directly throughout the codebase
settings = get_settings()
