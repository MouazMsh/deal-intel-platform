from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False, index=True)
    name_ar: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    emoji: Mapped[str | None] = mapped_column(sa.String(8), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
