from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BarResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    trades_count: int | None = None


class BackfillRequest(BaseModel):
    symbol: str
    timeframe: str = "1min"
    start: datetime
    end: datetime
    source: str = Field(default="auto", description="auto, polygon, finnhub, or synthetic")


class BackfillResponse(BaseModel):
    symbol: str
    timeframe: str
    inserted: int
    source: str
    start: datetime
    end: datetime


class StreamPreviewResponse(BaseModel):
    symbol: str
    timeframe: str
    source: str
    bars: list[BarResponse]


class MarketStatusResponse(BaseModel):
    exchange: str
    holiday: str | None = None
    is_open: bool
    session: str
    timezone: str
    timestamp: datetime
    provider: str
