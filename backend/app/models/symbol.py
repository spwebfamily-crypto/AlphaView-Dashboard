from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class Symbol(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "symbols"

    ticker: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(64))
    asset_type: Mapped[str] = mapped_column(String(32), default="equity", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

