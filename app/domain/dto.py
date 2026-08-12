"""Data transfer objects that cross the provider -> deal-engine boundary.

Providers (real or mock) never touch the database directly and never see
SQLAlchemy models. They return ``RawProductObservation`` objects; a later
phase's ``matching``/``pricing`` services are responsible for turning those
into ``CanonicalProduct`` / ``MarketplaceListing`` / ``PriceHistory`` rows.
This keeps the provider layer pure and trivially testable.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import Availability, DiscountType, MarketplaceCode


class RawProductObservation(BaseModel):
    """One provider's snapshot of one product listing at one point in time."""

    model_config = ConfigDict(frozen=True)

    marketplace_code: MarketplaceCode
    marketplace_product_id: str = Field(min_length=1)
    asin: str | None = None
    sku: str | None = None
    gtin: str | None = None

    title: str = Field(min_length=1)
    brand: str | None = None
    model: str | None = None
    category_hint: str | None = None

    image_url: str | None = None
    product_url: str = Field(min_length=1)

    seller_external_id: str | None = None
    seller_name: str | None = None
    seller_rating: float | None = Field(default=None, ge=0, le=5)
    seller_review_count: int | None = Field(default=None, ge=0)
    seller_fulfillment_type: str | None = None

    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    availability: Availability = Availability.UNKNOWN

    price: Decimal = Field(gt=0)
    original_price: Decimal | None = Field(default=None, gt=0)
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="SAR", min_length=3, max_length=3)

    coupon_code: str | None = None
    coupon_discount_value: Decimal | None = Field(default=None, gt=0)
    coupon_discount_type: DiscountType | None = None

    observed_at: datetime

    @field_validator("product_url")
    @classmethod
    def _require_http_url(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("product_url must be an absolute http(s) URL")
        return v

    @property
    def effective_price(self) -> Decimal:
        """Price after coupon, before shipping — what the deal engine scores."""
        if self.coupon_discount_value is None or self.coupon_discount_type is None:
            return self.price
        if self.coupon_discount_type == DiscountType.FIXED:
            return max(self.price - self.coupon_discount_value, Decimal("0"))
        # percentage
        return (self.price * (Decimal("100") - self.coupon_discount_value) / Decimal("100")).quantize(
            Decimal("0.01")
        )
