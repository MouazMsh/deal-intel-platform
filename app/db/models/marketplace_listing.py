from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.domain.enums import Availability


class MarketplaceListing(Base):
    """One marketplace's listing for a canonical product.

    ``match_confidence``/``match_method`` record how sure the (Phase 2)
    matching service is that this listing belongs to its ``canonical_product``
    — this replaces a separate PRODUCT_MATCH table (ARCHITECTURE.md §11).
    """

    __tablename__ = "marketplace_listings"
    __table_args__ = (
        sa.UniqueConstraint(
            "marketplace_id", "marketplace_product_id", name="uq_listing_marketplace_product_id"
        ),
        sa.Index("ix_listing_current_price", "current_price"),
        sa.Index("ix_listing_availability", "availability"),
        sa.Index("ix_listing_last_seen_at", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    canonical_product_id: Mapped[int] = mapped_column(
        sa.ForeignKey("canonical_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marketplace_id: Mapped[int] = mapped_column(
        sa.ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[int | None] = mapped_column(sa.ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True)

    marketplace_product_id: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    asin: Mapped[str | None] = mapped_column(sa.String(20), nullable=True, index=True)
    sku: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)

    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    normalized_title: Mapped[str] = mapped_column(sa.String(500), nullable=False, index=True)

    match_confidence: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    match_method: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    image_url: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    product_url: Mapped[str] = mapped_column(sa.String(1000), nullable=False)

    rating: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    availability: Mapped[Availability] = mapped_column(
        sa.Enum(Availability, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=Availability.UNKNOWN,
    )

    current_price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    shipping_cost: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False, default=Decimal("0"))
    final_price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False, default="SAR")

    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    blacklisted: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    canonical_product: Mapped["CanonicalProduct"] = relationship(back_populates="listings")
    marketplace: Mapped["Marketplace"] = relationship(back_populates="listings")
    seller: Mapped["Seller | None"] = relationship(back_populates="listings")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    deals: Mapped[list["Deal"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
