from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class BacktestRun(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backtest_runs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    symbol_scope: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict[str, float | int | str | bool | None] | None] = mapped_column(JSON)
    metrics: Mapped[dict[str, float | int | str | None] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

