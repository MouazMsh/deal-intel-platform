from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from app.core.exceptions import ProviderNotConfiguredError
from app.domain.dto import RawProductObservation


class AmazonProvider:
    """Real Amazon.sa provider — NOT YET IMPLEMENTED.

    Blocked on a business step, not an engineering one:

    * Requires an approved, active Amazon Associates account for the
      amazon.sa marketplace (with Associates' ongoing minimum-sales
      requirement to stay active).
    * The build target is Amazon's Creators API, not the legacy PA-API 5.0,
      which is being retired 2026-04-30 — building against it now would be
      wasted work.

    This class exists so ``ProviderRegistry`` has a real, typed target to
    switch to once ``AMAZON_PROVIDER_ENABLED=true`` and credentials exist
    (Phase 5). Every method intentionally raises ``NotImplementedError``
    rather than returning empty/fake data, so a misconfiguration fails
    loudly instead of silently returning nothing.
    """

    name: ClassVar[str] = "amazon_sa"
    is_mock: ClassVar[bool] = False

    def __init__(self, api_key: str, api_secret: str) -> None:
        if not api_key or not api_secret:
            raise ProviderNotConfiguredError(
                "AmazonProvider requires AMAZON_API_KEY and AMAZON_API_SECRET. "
                "These also require an approved Amazon Associates account for "
                "amazon.sa — see ARCHITECTURE.md §8/§12."
            )
        self._api_key = api_key
        self._api_secret = api_secret

    async def search_products(self, query: str, limit: int = 20) -> list[RawProductObservation]:
        raise NotImplementedError(
            "AmazonProvider is not implemented yet — see Phase 5 in the approved architecture."
        )

    async def get_product(self, marketplace_product_id: str) -> RawProductObservation | None:
        raise NotImplementedError(
            "AmazonProvider is not implemented yet — see Phase 5 in the approved architecture."
        )

    async def get_deals(self, limit: int = 50) -> list[RawProductObservation]:
        raise NotImplementedError(
            "AmazonProvider is not implemented yet — see Phase 5 in the approved architecture."
        )

    async def get_price(self, marketplace_product_id: str) -> Decimal | None:
        raise NotImplementedError(
            "AmazonProvider is not implemented yet — see Phase 5 in the approved architecture."
        )
