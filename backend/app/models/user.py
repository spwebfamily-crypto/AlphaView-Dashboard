from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class User(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    withdrawable_balance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stripe_connected_account_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stripe_transfers_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

