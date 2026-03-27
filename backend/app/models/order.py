from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class Order(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(128), index=True)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    order_type: Mapped[str] = mapped_column(String(32), nullable=False, default="market")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="PAPER")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

