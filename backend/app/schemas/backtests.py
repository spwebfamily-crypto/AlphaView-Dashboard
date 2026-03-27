from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1min"
    model_run_id: int | None = None
    trade_size: float = 10_000.0
    transaction_cost_bps: float = 1.0
    slippage_bps: float = 2.0
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_daily_loss: float = 1_500.0
    max_position_size: float = 10_000.0
    cooldown_minutes: int = 15
    max_exposure_per_symbol: float = 10_000.0
    buy_threshold: float = 0.55
    sell_threshold: float = 0.45


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: float
    drawdown: float


class BacktestTradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    entry_time: datetime
    exit_time: datetime | None
    entry_price: float
    exit_price: float | None
    quantity: float
    pnl: float | None
    pnl_pct: float | None


class BacktestRunResponse(BaseModel):
    id: int
    name: str
    status: str
    metrics: dict[str, float | int | str | None] | None = None
    config: dict[str, float | int | str | bool | None] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    equity_curve: list[EquityPoint] = []
    trades: list[BacktestTradeResponse] = []
