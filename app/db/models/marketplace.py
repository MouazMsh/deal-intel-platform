from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.domain.enums import MarketplaceCode


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[MarketplaceCode] = mapped_column(
        sa.Enum(MarketplaceCode, native_enum=False, length=32, validate_strings=True),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    base_currency: Mapped[str] = mapped_column(sa.String(3), nullable=False, default="SAR")
    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=sa.func.now())

    sellers: Mapped[list["Seller"]] = relationship(back_populates="marketplace")
    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="marketplace")
