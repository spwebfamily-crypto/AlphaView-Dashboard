from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class WithdrawalRequest(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "withdrawal_requests"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    stripe_account_id: Mapped[str | None] = mapped_column(String(255))
    stripe_transfer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_payout_id: Mapped[str | None] = mapped_column(String(255))
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
