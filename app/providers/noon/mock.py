from __future__ import annotations

import logging
from decimal import Decimal
from typing import ClassVar

from pydantic import ValidationError

from app.domain.dto import RawProductObservation
from app.providers.noon.fixtures import RAW_FIXTURES

logger = logging.getLogger(__name__)


class MockNoonProvider:
    """Fixture-backed stand-in for the real Noon provider.

    Symmetric with ``MockAmazonProvider`` by design — Noon is a first-class
    provider, not an afterthought, per the approved architecture (§12).
    """

    name: ClassVar[str] = "noon_sa"
    is_mock: ClassVar[bool] = True

    def _parsed_fixtures(self) -> list[RawProductObservation]:
        observations: list[RawProductObservation] = []
        for raw in RAW_FIXTURES:
            try:
                observations.append(RawProductObservation.model_validate(raw))
            except ValidationError as exc:
                logger.warning(
                    "mock_noon_fixture_skipped",
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
