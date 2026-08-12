from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime


class CanonicalProduct(Base):
    """The marketplace-neutral product identity (e.g. "Sony WH-1000XM5").

    Marketplace-specific price/seller/stock/URL live on ``MarketplaceListing``
    rows that point back here — see ARCHITECTURE.md §11 for why this is a
    real table rather than a self-referencing PRODUCT_MATCH join.
    """

    __tablename__ = "canonical_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_title: Mapped[str] = mapped_column(sa.String(300), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    gtin: Mapped[str | None] = mapped_column(sa.String(14), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=sa.func.now())

    category: Mapped["Category | None"] = relationship()
    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="canonical_product")
