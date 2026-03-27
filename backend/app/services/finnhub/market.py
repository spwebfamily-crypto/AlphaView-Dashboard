from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.services.finnhub.client import FinnhubClient


@dataclass(slots=True)
class FinnhubQuote:
    timestamp: datetime
    current_price: Decimal
    high: Decimal
    low: Decimal
    open: Decimal
    previous_close: Decimal | None


@dataclass(slots=True)
class FinnhubMarketStatus:
    exchange: str
    holiday: str | None
    is_open: bool
    session: str
    timezone_name: str
    timestamp: datetime


def fetch_quote(client: FinnhubClient, *, symbol: str) -> FinnhubQuote:
    payload = client.get_quote(symbol=symbol.upper())
    quote_timestamp = payload.get("t")
    timestamp = (
        datetime.fromtimestamp(quote_timestamp, tz=timezone.utc)
        if quote_timestamp
        else datetime.now(timezone.utc)
    )
    return FinnhubQuote(
        timestamp=timestamp,
        current_price=Decimal(str(payload.get("c", 0.0))),
        high=Decimal(str(payload.get("h", 0.0))),
        low=Decimal(str(payload.get("l", 0.0))),
        open=Decimal(str(payload.get("o", 0.0))),
        previous_close=Decimal(str(payload["pc"])) if payload.get("pc") is not None else None,
    )


def fetch_market_status(client: FinnhubClient, *, exchange: str) -> FinnhubMarketStatus:
    payload = client.get_market_status(exchange=exchange.upper())
    status_timestamp = payload.get("t")
    timestamp = (
        datetime.fromtimestamp(status_timestamp, tz=timezone.utc)
        if status_timestamp
        else datetime.now(timezone.utc)
    )
    return FinnhubMarketStatus(
        exchange=payload.get("exchange", exchange.upper()),
        holiday=payload.get("holiday"),
        is_open=bool(payload.get("isOpen", False)),
        session=str(payload.get("session") or "unknown"),
        timezone_name=str(payload.get("timezone", "UTC")),
        timestamp=timestamp,
    )
