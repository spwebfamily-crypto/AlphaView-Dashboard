from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DemoSeedRequest(BaseModel):
    symbols: list[str] = ["SAP.DE", "MC.PA", "AIR.PA"]
    timeframe: str = "1min"
    days: int = 5


class SummaryCard(BaseModel):
    label: str
    value: float | int | str
    delta: float | None = None


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    mode: str
    summary_cards: list[SummaryCard]
    equity_curve: list[dict[str, str | float]]
    pnl_curve: list[dict[str, str | float]]
    win_loss_distribution: list[dict[str, str | float]]
    latest_signals: list[dict[str, str | float | None]]
    positions: list[dict[str, str | float | None]]
    backtests: list[dict[str, str | float | int | None]]
    models: list[dict[str, str | float | int | None]]
    logs: list[dict[str, str]]
