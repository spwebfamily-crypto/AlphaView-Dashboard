from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BrokerStatusResponse(BaseModel):
    adapter: str
    mode: str
    connected: bool
    details: str


class OrderCreateRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    limit_price: float | None = None


class OrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    status: str
    mode: str
    submitted_at: datetime | None = None


class ExecutionResponse(BaseModel):
    id: int
    order_id: int
    executed_at: datetime
    price: float
    quantity: float
    fees: float | None = None


class PositionResponse(BaseModel):
    id: int
    symbol: str
    status: str
    quantity: float
    average_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    realized_pnl: float | None = None
    opened_at: datetime | None = None
