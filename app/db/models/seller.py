from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Seller(Base):
    __tablename__ = "sellers"
    __table_args__ = (
        sa.UniqueConstraint("marketplace_id", "external_seller_id", name="uq_seller_marketplace_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    marketplace_id: Mapped[int] = mapped_column(sa.ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False)
    external_seller_id: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    rating: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    fulfillment_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    blacklisted: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    marketplace: Mapped["Marketplace"] = relationship(back_populates="sellers")
    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="seller")
