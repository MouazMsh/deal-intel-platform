"""The MarketplaceProvider interface.

Every marketplace (real or mock) implements this. The deal engine (Phase 2)
depends only on this Protocol, never on a concrete provider class — adding a
future marketplace (Jarir, Extra, ...) means adding an implementation here,
never touching pricing/scoring/telegram.
"""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar, Protocol, runtime_checkable

from app.domain.dto import RawProductObservation


@runtime_checkable
class MarketplaceProvider(Protocol):
    name: ClassVar[str]
    # True for mock providers. ProviderRegistry uses this to enforce that no
    # mock provider can ever be selected when ENVIRONMENT=production.
    is_mock: ClassVar[bool]

    async def search_products(self, query: str, limit: int = 20) -> list[RawProductObservation]:
        """Search for products matching a free-text query."""
        ...

    async def get_product(self, marketplace_product_id: str) -> RawProductObservation | None:
        """Fetch a single product by its marketplace-native ID."""
        ...

    async def get_deals(self, limit: int = 50) -> list[RawProductObservation]:
        """Fetch products currently flagged as deals/discounted by the marketplace."""
        ...

    async def get_price(self, marketplace_product_id: str) -> Decimal | None:
        """Fetch just the current price for a product, if available."""
        ...
