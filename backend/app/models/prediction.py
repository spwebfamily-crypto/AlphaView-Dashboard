from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class Prediction(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "predictions"

    model_run_id: Mapped[int | None] = mapped_column(ForeignKey("model_runs.id"), index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(64))
    probability_up: Mapped[float | None] = mapped_column(Numeric(10, 6))
    probability_down: Mapped[float | None] = mapped_column(Numeric(10, 6))
    raw_output: Mapped[dict[str, float | int | str | None] | None] = mapped_column(JSON)

