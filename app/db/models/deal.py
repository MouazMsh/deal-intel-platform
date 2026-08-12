from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.domain.enums import DealClassification, DealGrade, LifecycleStatus


class Deal(Base):
    """A scored evaluation of one listing at one point in time.

    Re-derivable from ``MarketplaceListing`` + ``PriceHistory`` — this table
    stores the *decision*, not a second source of truth for price/product
    data. ``score_breakdown``/``confidence_breakdown`` are JSON because their
    shape is config-driven (adding a scoring factor shouldn't need a
    migration); every fixed-shape field gets a real column, per
    ARCHITECTURE.md §4-8.

    Scoring/confidence/lifecycle *logic* lands in Phase 2 — this table exists
    now because the schema, not the algorithm, needed to be settled first.
    """

    __tablename__ = "deals"
    __table_args__ = (
        sa.Index("ix_deal_score", "deal_score"),
        sa.Index("ix_deal_lifecycle_status", "lifecycle_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # One Deal row per listing, continuously re-scored -- not an append-only
    # evaluation history (ARCHITECTURE.md: "re-derivable, not a second
    # source of truth"). unique=True enforces the get-or-create-one
    # invariant app/deals/pipeline.py relies on at the DB level too.
    listing_id: Mapped[int] = mapped_column(
        sa.ForeignKey("marketplace_listings.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    deal_score: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    deal_confidence: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    deal_grade: Mapped[DealGrade | None] = mapped_column(
        sa.Enum(DealGrade, native_enum=False, length=10, validate_strings=True), nullable=True
    )
    deal_classification: Mapped[DealClassification | None] = mapped_column(
        sa.Enum(DealClassification, native_enum=False, length=20, validate_strings=True), nullable=True
    )

    score_breakdown: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    confidence_breakdown: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    discount_pct_advertised: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), nullable=True)
    discount_pct_vs_avg30: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), nullable=True)
    discount_pct_vs_min: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), nullable=True)

    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        sa.Enum(LifecycleStatus, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=LifecycleStatus.DISCOVERED,
    )
    rejection_reason: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)

    first_qualified_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    listing: Mapped["MarketplaceListing"] = relationship(back_populates="deals")
    published_deal: Mapped["PublishedDeal | None"] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan"
    )
