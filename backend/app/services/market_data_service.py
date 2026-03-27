from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

import numpy as np
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market_bar import MarketDataBar
from app.models.symbol import Symbol
from app.services.finnhub.client import FinnhubClient
from app.services.finnhub.historical import normalize_finnhub_candles
from app.services.finnhub.market import (
    FinnhubMarketStatus,
    fetch_market_status as fetch_finnhub_market_status,
    fetch_quote as fetch_finnhub_quote,
)
from app.services.polygon.client import PolygonClient
from app.services.polygon.historical import normalize_polygon_aggregates
from app.services.system_log_service import log_event
from app.utils.time import ensure_utc, generate_intraday_timestamps, timeframe_to_minutes


@dataclass(slots=True)
class NormalizedBar:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal | None = None
    trades_count: int | None = None


def ensure_symbol(session: Session, ticker: str) -> Symbol:
    symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker.upper()))
    if symbol is not None:
        return symbol

    symbol = Symbol(ticker=ticker.upper(), name=ticker.upper(), exchange="NASDAQ")
    session.add(symbol)
    session.commit()
    session.refresh(symbol)
    return symbol


def parse_timeframe(timeframe: str) -> tuple[int, str]:
    minutes = timeframe_to_minutes(timeframe)
    if timeframe.lower() == "1day":
        return 1, "day"
    if minutes % 60 == 0 and minutes != 390:
        return int(minutes / 60), "hour"
    return minutes, "minute"


def generate_synthetic_bars(
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[NormalizedBar]:
    step_minutes = timeframe_to_minutes(timeframe)
    timestamps = generate_intraday_timestamps(start, end, step_minutes if step_minutes != 390 else 390)
    seed = abs(hash((symbol.upper(), timeframe, start.date().isoformat(), end.date().isoformat()))) % (2**32)
    rng = np.random.default_rng(seed)
    base_price = 75 + (sum(ord(char) for char in symbol.upper()) % 250)
    drift = 0.0002 + ((sum(ord(char) for char in symbol.upper()) % 7) / 10000)
    close_price = float(base_price)
    bars: list[NormalizedBar] = []

    for timestamp in timestamps:
        open_price = close_price
        shock = rng.normal(loc=drift, scale=0.0025 if timeframe == "1min" else 0.006)
        close_price = max(5.0, open_price * (1 + shock))
        high = max(open_price, close_price) * (1 + abs(rng.normal(0.0008, 0.0004)))
        low = min(open_price, close_price) * (1 - abs(rng.normal(0.0008, 0.0004)))
        volume = int(max(1_000, rng.normal(75_000, 18_000)))
        bars.append(
            NormalizedBar(
                symbol=symbol.upper(),
                timeframe=timeframe,
                timestamp=ensure_utc(timestamp),
                open=Decimal(f"{open_price:.6f}"),
                high=Decimal(f"{high:.6f}"),
                low=Decimal(f"{low:.6f}"),
                close=Decimal(f"{close_price:.6f}"),
                volume=volume,
                vwap=Decimal(f"{((open_price + high + low + close_price) / 4):.6f}"),
                trades_count=int(max(1, volume / 130)),
            )
        )
    return bars


def resolve_source(settings: Settings, source: str) -> Literal["polygon", "finnhub", "synthetic"]:
    normalized = source.lower().strip()
    if normalized == "polygon":
        if not settings.polygon_api_key:
            raise RuntimeError("Requested Polygon source but POLYGON_API_KEY is not configured.")
        return "polygon"
    if normalized == "finnhub":
        if not settings.finnhub_api_key:
            raise RuntimeError("Requested Finnhub source but FINNHUB_API_KEY is not configured.")
        return "finnhub"
    if normalized == "synthetic":
        return "synthetic"
    return "polygon" if settings.polygon_api_key else "synthetic"


def fetch_historical_bars(
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    source: str,
) -> tuple[list[NormalizedBar], str]:
    selected_source = resolve_source(settings, source)
    if selected_source == "polygon":
        multiplier, timespan = parse_timeframe(timeframe)
        polygon_bars = normalize_polygon_aggregates(
            PolygonClient(settings),
            symbol=symbol.upper(),
            multiplier=multiplier,
            timespan=timespan,
            start=ensure_utc(start),
            end=ensure_utc(end),
        )
        return (
            [
                NormalizedBar(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    timestamp=bar.timestamp,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    vwap=bar.vwap,
                    trades_count=bar.trades_count,
                )
                for bar in polygon_bars
            ],
            "polygon",
        )
    if selected_source == "finnhub":
        finnhub_bars = normalize_finnhub_candles(
            FinnhubClient(settings),
            symbol=symbol.upper(),
            timeframe=timeframe,
            start=ensure_utc(start),
            end=ensure_utc(end),
        )
        return (
            [
                NormalizedBar(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    timestamp=bar.timestamp,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    vwap=None,
                    trades_count=None,
                )
                for bar in finnhub_bars
            ],
            "finnhub",
        )
    return generate_synthetic_bars(symbol=symbol, timeframe=timeframe, start=start, end=end), "synthetic"


def upsert_bars(session: Session, *, symbol: str, timeframe: str, bars: list[NormalizedBar]) -> int:
    if not bars:
        return 0

    symbol_row = ensure_symbol(session, symbol)
    timestamps = [bar.timestamp for bar in bars]
    existing_rows = session.scalars(
        select(MarketDataBar).where(
            and_(
                MarketDataBar.symbol_id == symbol_row.id,
                MarketDataBar.timeframe == timeframe,
                MarketDataBar.timestamp >= min(timestamps),
                MarketDataBar.timestamp <= max(timestamps),
            )
        )
    )
    existing_by_timestamp = {row.timestamp: row for row in existing_rows}

    inserted = 0
    for bar in bars:
        row = existing_by_timestamp.get(bar.timestamp)
        if row is None:
            row = MarketDataBar(
                symbol_id=symbol_row.id,
                timeframe=timeframe,
                timestamp=bar.timestamp,
            )
            session.add(row)
            inserted += 1

        row.open = bar.open
        row.high = bar.high
        row.low = bar.low
        row.close = bar.close
        row.volume = bar.volume
        row.vwap = bar.vwap
        row.trades_count = bar.trades_count

    session.commit()
    return inserted


def backfill_market_data(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    source: str = "auto",
) -> tuple[int, str]:
    bars, selected_source = fetch_historical_bars(
        settings,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        source=source,
    )
    inserted = upsert_bars(session, symbol=symbol, timeframe=timeframe, bars=bars)
    log_event(
        session,
        level="INFO",
        source="market_data",
        event_type="backfill_completed",
        message=f"Backfilled {inserted} bars for {symbol.upper()} {timeframe}",
        context={
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "inserted": inserted,
            "source": selected_source,
        },
    )
    return inserted, selected_source


def get_market_status(settings: Settings, *, exchange: str = "US") -> tuple[FinnhubMarketStatus, str]:
    if not settings.finnhub_api_key:
        raise RuntimeError("FINNHUB_API_KEY is required to fetch market status.")
    status = fetch_finnhub_market_status(FinnhubClient(settings), exchange=exchange.upper())
    return status, "finnhub"


def configured_market_data_sources(settings: Settings) -> list[str]:
    sources: list[str] = []
    if settings.polygon_api_key:
        sources.append("polygon")
    if settings.finnhub_api_key:
        sources.append("finnhub")
    sources.append("synthetic")
    return sources


def get_bars(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
) -> list[tuple[MarketDataBar, str]]:
    symbol_row = ensure_symbol(session, symbol)
    query = select(MarketDataBar).where(
        and_(MarketDataBar.symbol_id == symbol_row.id, MarketDataBar.timeframe == timeframe)
    )
    if start is not None:
        query = query.where(MarketDataBar.timestamp >= ensure_utc(start))
    if end is not None:
        query = query.where(MarketDataBar.timestamp <= ensure_utc(end))
    query = query.order_by(MarketDataBar.timestamp.asc()).limit(limit)
    return [(row, symbol_row.ticker) for row in session.scalars(query)]


def latest_price(session: Session, settings: Settings, symbol: str, timeframe: str = "1min") -> float:
    symbol_row = ensure_symbol(session, symbol)
    latest_bar = session.scalar(
        select(MarketDataBar)
        .where(and_(MarketDataBar.symbol_id == symbol_row.id, MarketDataBar.timeframe == timeframe))
        .order_by(MarketDataBar.timestamp.desc())
        .limit(1)
    )
    if latest_bar is None:
        if settings.finnhub_api_key:
            try:
                return float(fetch_finnhub_quote(FinnhubClient(settings), symbol=symbol).current_price)
            except Exception:
                pass
        generated = generate_synthetic_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc),
        )
        return float(generated[0].close) if generated else 100.0
    return float(latest_bar.close)
