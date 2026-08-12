"""ProviderRegistry — the single place that decides which provider
implementation to use, and the enforcement point for Guardrail #2
(mock-data protection, provider side).

Two independent checks happen here:

1. Resolve which concrete provider a marketplace maps to, based on config.
2. Refuse — unconditionally, at call time — to return a mock provider while
   ``ENVIRONMENT=production``. This makes "a production run accidentally
   used mock data" structurally impossible rather than merely unlikely:
   there is no code path where a production run can hold a mock provider
   instance at all.

Noon has a third layer on top: ``core.config.Settings`` already refuses to
load if ``NOON_PROVIDER_ENABLED=true``, so in practice this registry never
even reaches the branch that would construct a real ``NoonProvider`` — but
the check stays here too, as defense-in-depth documented in
``providers/noon/provider.py``.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import MockProviderInProductionError
from app.domain.enums import Environment, MarketplaceCode
from app.providers.amazon.mock import MockAmazonProvider
from app.providers.amazon.provider import AmazonProvider
from app.providers.base import MarketplaceProvider
from app.providers.noon.mock import MockNoonProvider
from app.providers.noon.provider import NoonProvider


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_provider(self, marketplace_code: MarketplaceCode) -> MarketplaceProvider:
        provider = self._resolve(marketplace_code)
        self._enforce_no_mock_in_production(provider)
        return provider

    def _resolve(self, marketplace_code: MarketplaceCode) -> MarketplaceProvider:
        if marketplace_code == MarketplaceCode.AMAZON_SA:
            if self._settings.AMAZON_PROVIDER_ENABLED:
                return AmazonProvider(
                    api_key=self._settings.AMAZON_API_KEY,
                    api_secret=self._settings.AMAZON_API_SECRET,
                )
            return MockAmazonProvider()

        if marketplace_code == MarketplaceCode.NOON_SA:
            if self._settings.NOON_PROVIDER_ENABLED:
                # Should be unreachable: Settings already refuses to load
                # with NOON_PROVIDER_ENABLED=true. Kept as defense-in-depth.
                return NoonProvider()
            return MockNoonProvider()

        raise ValueError(f"Unknown marketplace code: {marketplace_code!r}")

    def _enforce_no_mock_in_production(self, provider: MarketplaceProvider) -> None:
        if self._settings.ENVIRONMENT == Environment.PRODUCTION and provider.is_mock:
            raise MockProviderInProductionError(
                f"Refusing to use mock provider {provider.name!r} with "
                "ENVIRONMENT=production. This is Guardrail #2 (provider-level "
                "gate) — see OPERATIONAL_GUARDRAILS.md."
            )
