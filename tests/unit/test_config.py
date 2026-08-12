from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import make_settings


def test_default_development_settings_load_cleanly() -> None:
    settings = make_settings()
    assert settings.ENVIRONMENT.value == "test"
    assert settings.NOON_PROVIDER_ENABLED is False
    assert settings.DRY_RUN is True


def test_noon_provider_enabled_true_is_hard_blocked() -> None:
    with pytest.raises(ValidationError, match="NOON_PROVIDER_ENABLED cannot be true"):
        make_settings(NOON_PROVIDER_ENABLED=True)


def test_production_requires_postgres_database_url() -> None:
    with pytest.raises(ValidationError, match="requires a PostgreSQL DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="sqlite+aiosqlite:///./prod.db",
            TELEGRAM_CHANNEL_ID="@somechannel",
            DRY_RUN=False,
        )


def test_production_with_postgres_url_and_channel_is_valid() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
        TELEGRAM_CHANNEL_ID="@somechannel",
        DRY_RUN=False,
    )
    assert settings.ENVIRONMENT.value == "production"


def test_production_requires_telegram_channel_id() -> None:
    with pytest.raises(ValidationError, match="requires TELEGRAM_CHANNEL_ID"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
            TELEGRAM_CHANNEL_ID="",
            DRY_RUN=False,
        )


def test_non_production_without_dry_run_or_test_channel_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Non-production environments must"):
        make_settings(DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="")


def test_non_production_with_test_channel_and_dry_run_false_is_valid() -> None:
    settings = make_settings(DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="@test_channel")
    assert settings.TELEGRAM_TEST_CHANNEL_ID == "@test_channel"
