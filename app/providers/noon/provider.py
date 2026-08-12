from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from app.core.exceptions import NoonProviderBlockedError
from app.domain.dto import RawProductObservation


class NoonProvider:
    """Real Noon Saudi Arabia provider — BLOCKED, not merely unimplemented.

    No compliant, official product/price data source exists for Noon at
    this time. What exists is affiliate **link generation** through
    third-party affiliate networks (ArabClicks, DCMnetwork, admitad, etc.),
    which is not a product/price API. Building this against scraping,
    CAPTCHA bypass, anti-bot evasion, or an undocumented endpoint is
    explicitly prohibited — see CONTRIBUTING.md's standing policy.

    Unlike ``AmazonProvider`` (which raises per-method), this class refuses
    to even be *constructed*: there is currently no configuration that makes
    it legitimate to instantiate. ``ProviderRegistry`` never calls this
    constructor while ``NOON_PROVIDER_ENABLED`` is false — which it always
    is, because ``core.config.Settings`` hard-rejects setting it to true.
    This class is defense-in-depth on top of that, not the primary control.
    """

    name: ClassVar[str] = "noon_sa"
    is_mock: ClassVar[bool] = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NoonProviderBlockedError(
            "NoonProvider cannot be instantiated: no compliant Noon "
            "product/price data source exists yet. See CONTRIBUTING.md."
        )

    async def search_products(self, query: str, limit: int = 20) -> list[RawProductObservation]:
        raise NoonProviderBlockedError("NoonProvider is blocked — see CONTRIBUTING.md.")

    async def get_product(self, marketplace_product_id: str) -> RawProductObservation | None:
        raise NoonProviderBlockedError("NoonProvider is blocked — see CONTRIBUTING.md.")

    async def get_deals(self, limit: int = 50) -> list[RawProductObservation]:
        raise NoonProviderBlockedError("NoonProvider is blocked — see CONTRIBUTING.md.")

    async def get_price(self, marketplace_product_id: str) -> Decimal | None:
        raise NoonProviderBlockedError("NoonProvider is blocked — see CONTRIBUTING.md.")
