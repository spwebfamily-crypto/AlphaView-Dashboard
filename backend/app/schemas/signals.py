from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalGenerationRequest(BaseModel):
    symbol: str
    timeframe: str = "1min"
    model_run_id: int | None = None
    buy_threshold: float = 0.55
    sell_threshold: float = 0.45


class SignalResponse(BaseModel):
    id: int
    symbol: str
    timestamp: datetime
    signal_type: str
    confidence: float | None = None
    reason: str | None = None
    status: str
