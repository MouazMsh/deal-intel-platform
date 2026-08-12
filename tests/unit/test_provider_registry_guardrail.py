from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import MockProviderInProductionError, NoonProviderBlockedError
from app.domain.enums import MarketplaceCode
from app.providers.amazon.mock import MockAmazonProvider
from app.providers.noon.mock import MockNoonProvider
from app.providers.registry import ProviderRegistry
from tests.conftest import make_settings


def test_development_resolves_mock_amazon_provider() -> None:
    registry = ProviderRegistry(make_settings(ENVIRONMENT="development"))
    provider = registry.get_provider(MarketplaceCode.AMAZON_SA)
    assert isinstance(provider, MockAmazonProvider)
    assert provider.is_mock is True


def test_development_resolves_mock_noon_provider() -> None:
    registry = ProviderRegistry(make_settings(ENVIRONMENT="development"))
    provider = registry.get_provider(MarketplaceCode.NOON_SA)
    assert isinstance(provider, MockNoonProvider)
    assert provider.is_mock is True


def test_production_with_mock_amazon_provider_is_blocked() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
        TELEGRAM_CHANNEL_ID="@channel",
        DRY_RUN=False,
        AMAZON_PROVIDER_ENABLED=False,  # real provider not enabled -> would resolve to mock
    )
    registry = ProviderRegistry(settings)
    with pytest.raises(MockProviderInProductionError):
        registry.get_provider(MarketplaceCode.AMAZON_SA)


def test_production_noon_is_blocked_even_via_defense_in_depth_path() -> None:
    """Settings already refuses NOON_PROVIDER_ENABLED=true. This test proves
    the registry's own defense-in-depth check also fires, by constructing a
    Settings object that bypasses field validation (model_construct) to
    simulate what would happen if that first layer were ever removed.
    """
    settings = Settings.model_construct(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
        TELEGRAM_CHANNEL_ID="@channel",
        DRY_RUN=False,
        AMAZON_PROVIDER_ENABLED=False,
        AMAZON_API_KEY="",
        AMAZON_API_SECRET="",
        NOON_PROVIDER_ENABLED=True,  # only reachable by bypassing validation
        NOON_API_KEY="",
        NOON_API_SECRET="",
    )
    registry = ProviderRegistry(settings)
    with pytest.raises(NoonProviderBlockedError):
        registry.get_provider(MarketplaceCode.NOON_SA)


def test_unknown_marketplace_code_raises_value_error() -> None:
    registry = ProviderRegistry(make_settings())
    with pytest.raises(ValueError, match="Unknown marketplace code"):
        registry.get_provider("not_a_real_marketplace")  # type: ignore[arg-type]
