from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_mixins import PrimaryKeyMixin, TimestampMixin


class FeatureRow(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feature_rows"
    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "timestamp", "pipeline_version", name="uq_feature_row"),
    )

    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    source_bar_id: Mapped[int | None] = mapped_column(ForeignKey("market_data_bars.id"))
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict[str, float | int | str | None]] = mapped_column(JSON, nullable=False)

