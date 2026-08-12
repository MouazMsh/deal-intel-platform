from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.domain.enums import PublishedDealStatus


class PublishedDeal(Base):
    """A Telegram post for a Deal. One row per Deal — price-change/expiry
    edits the existing message (see telegram/publisher.py in Phase 3) rather
    than creating a new row, which is what keeps publishing idempotent.
    """

    __tablename__ = "published_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    telegram_channel_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    tracking_slug: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True, index=True)

    published_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[PublishedDealStatus] = mapped_column(
        sa.Enum(PublishedDealStatus, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=PublishedDealStatus.ACTIVE,
    )
    click_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    deal: Mapped["Deal"] = relationship(back_populates="published_deal")
