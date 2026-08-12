from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.domain.enums import Availability, DiscountType


class PriceHistory(Base):
    """One observed price point for a listing.

    Coupon fields live directly on this table for Phase 1 — a normalized
    ``Coupon`` table is deferred to Phase 2 per the approved MVP scope
    (coupon *calculation* logic is a Phase 2 concern; Phase 1 only needs
    somewhere to record what was observed).
    """

    __tablename__ = "price_history"
    __table_args__ = (sa.Index("ix_price_history_listing_observed_at", "listing_id", "observed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        sa.ForeignKey("marketplace_listings.id", ondelete="CASCADE"), nullable=False, index=True
    )

    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    shipping_cost: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False, default=Decimal("0"))
    effective_price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)

    coupon_code: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    coupon_discount_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    coupon_discount_type: Mapped[DiscountType | None] = mapped_column(
        sa.Enum(DiscountType, native_enum=False, length=20, validate_strings=True), nullable=True
    )

    availability: Mapped[Availability] = mapped_column(
        sa.Enum(Availability, native_enum=False, length=20, validate_strings=True), nullable=False
    )
    source: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    listing: Mapped["MarketplaceListing"] = relationship(back_populates="price_history")
