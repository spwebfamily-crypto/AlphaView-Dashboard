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
    source: str = Field(default="auto", description="auto, eodhd, ibkr, polygon, finnhub, or synthetic")


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


class SymbolLookupResponse(BaseModel):
    ticker: str
    name: str | None = None
    exchange: str | None = None
    asset_type: str
    is_active: bool
    market: str | None = None
    primary_exchange: str | None = None
    security_type: str | None = None
    currency: str | None = None
    round_lot_size: int | None = None
    minimum_order_size: int | None = None
    last_updated_utc: datetime | None = None
    last_price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    quote_timestamp: datetime | None = None
    quote_source: str | None = None


class MarketUniverseResponse(BaseModel):
    items: list[SymbolLookupResponse]
    next_cursor: str | None = None
    source: str
    as_of: datetime
