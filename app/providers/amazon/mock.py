from __future__ import annotations

import logging
from decimal import Decimal
from typing import ClassVar

from pydantic import ValidationError

from app.domain.dto import RawProductObservation
from app.providers.amazon.fixtures import RAW_FIXTURES

logger = logging.getLogger(__name__)


class MockAmazonProvider:
    """Fixture-backed stand-in for the real Amazon provider.

    Used automatically whenever ``AMAZON_PROVIDER_ENABLED=false`` (the
    default). Deliberately mirrors real-world resilience requirements: one
    malformed fixture is included and skipped with a logged warning rather
    than raising, so this also doubles as a test of "one bad product must
    not crash the batch" even before the real deal pipeline exists.
    """

    name: ClassVar[str] = "amazon_sa"
    is_mock: ClassVar[bool] = True

    def _parsed_fixtures(self) -> list[RawProductObservation]:
        observations: list[RawProductObservation] = []
        for raw in RAW_FIXTURES:
            try:
                observations.append(RawProductObservation.model_validate(raw))
            except ValidationError as exc:
                logger.warning(
                    "mock_amazon_fixture_skipped",
                    extra={"marketplace_product_id": raw.get("marketplace_product_id"), "error": str(exc)},
                )
        return observations

    async def search_products(self, query: str, limit: int = 20) -> list[RawProductObservation]:
        results = [o for o in self._parsed_fixtures() if query.lower() in o.title.lower()]
        return results[:limit]

    async def get_product(self, marketplace_product_id: str) -> RawProductObservation | None:
        for observation in self._parsed_fixtures():
            if observation.marketplace_product_id == marketplace_product_id:
                return observation
        return None

    async def get_deals(self, limit: int = 50) -> list[RawProductObservation]:
        deals = [
            o
            for o in self._parsed_fixtures()
            if o.original_price is not None and o.original_price > o.price
        ]
        return deals[:limit]

    async def get_price(self, marketplace_product_id: str) -> Decimal | None:
        product = await self.get_product(marketplace_product_id)
        return product.price if product else None
