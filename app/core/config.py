"""Application configuration.

Every business parameter is env-driven (12-factor style). Nothing here has a
real secret as a default — defaults are either safe placeholders or the
safest possible behavior (e.g. ``DRY_RUN`` defaults to ``True``).

Two guardrails from the approved architecture are enforced directly in this
file, as validators that raise at settings-load time rather than as
conventions someone has to remember:

1. Production must use a PostgreSQL ``DATABASE_URL`` (Neon) — SQLite is
   development/testing only.
2. ``NOON_PROVIDER_ENABLED`` can never be set to ``true`` — no compliant
   Noon product/price data source exists yet (see CONTRIBUTING.md). This is
   intentional and will only change when a documented compliant source is
   approved.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.enums import Environment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Runtime ---
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Riyadh"

    # --- Database ---
    # Dev/test default: local SQLite via aiosqlite. Production MUST be a
    # Neon (or other) PostgreSQL URL — enforced below, not just documented.
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""
    # Production public channel ONLY. Never used outside ENVIRONMENT=production
    # — see telegram/publisher.py Gate B.
    TELEGRAM_CHANNEL_ID: str = ""
    # Private channel for manual verification in non-production environments.
    TELEGRAM_TEST_CHANNEL_ID: str = ""
    # Defaults to True on purpose: an unconfigured/misconfigured environment
    # should never be able to silently send real Telegram messages.
    DRY_RUN: bool = True

    # --- Providers ---
    AMAZON_PROVIDER_ENABLED: bool = False
    AMAZON_API_KEY: str = ""
    AMAZON_API_SECRET: str = ""

    # Hard-blocked below. Do not remove the validator without an approved,
    # documented compliant Noon data source (see CONTRIBUTING.md).
    NOON_PROVIDER_ENABLED: bool = False
    NOON_API_KEY: str = ""
    NOON_API_SECRET: str = ""

    # --- Deal engine (used starting Phase 2; declared now so .env.example
    # documents the full configuration surface from day one) ---
    PRICE_HISTORY_DAYS: int = 90
    MIN_DEAL_SCORE: int = 70
    MIN_CONFIDENCE_FOR_GRADE: int = Field(default=50, ge=0, le=100)
    FLASH_DEAL_THRESHOLD: int = 20
    REPUBLISH_COOLDOWN_HOURS: int = 24
    FRESHNESS_FRESH_MINUTES: int = 15
    FRESHNESS_RECENT_MINUTES: int = 60

    # --- Scheduler (used starting Phase 4; see ARCHITECTURE.md §13 for the
    # Neon CU-hour math behind this default) ---
    SCAN_FREQUENCY_MINUTES: int = 30

    @model_validator(mode="after")
    def _enforce_noon_hard_block(self) -> "Settings":
        if self.NOON_PROVIDER_ENABLED:
            raise ValueError(
                "NOON_PROVIDER_ENABLED cannot be true. No compliant Noon "
                "product/price data source exists yet — Noon only offers "
                "affiliate link generation, not a product/price API. This is "
                "a standing project policy (see CONTRIBUTING.md), not a bug. "
                "Do not work around this validator."
            )
        return self

    @model_validator(mode="after")
    def _enforce_production_database(self) -> "Settings":
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if not self.DATABASE_URL.startswith("postgresql"):
                raise ValueError(
                    "ENVIRONMENT=production requires a PostgreSQL DATABASE_URL "
                    "(Neon). SQLite is for development/testing only."
                )
        return self

    @model_validator(mode="after")
    def _enforce_production_telegram_channel(self) -> "Settings":
        if self.ENVIRONMENT == Environment.PRODUCTION and not self.TELEGRAM_CHANNEL_ID:
            raise ValueError("ENVIRONMENT=production requires TELEGRAM_CHANNEL_ID to be set.")
        return self

    @model_validator(mode="after")
    def _enforce_non_production_never_targets_prod_channel(self) -> "Settings":
        # Belt-and-suspenders: a non-production run is only ever allowed to
        # either dry-run or target the separate test channel. It is never
        # valid configuration for a non-prod run to have no safe outlet.
        if self.ENVIRONMENT != Environment.PRODUCTION:
            if not self.DRY_RUN and not self.TELEGRAM_TEST_CHANNEL_ID:
                raise ValueError(
                    "Non-production environments must either set DRY_RUN=true "
                    "or configure TELEGRAM_TEST_CHANNEL_ID. Publishing to the "
                    "production channel from a non-production environment is "
                    "not supported by this configuration model."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings singleton.

    Tests that need a *different* configuration should construct ``Settings``
    directly (see tests/conftest.py) rather than mutating this cache.
    """

    return Settings()
