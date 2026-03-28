from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.market_data import (
    BackfillRequest,
    BackfillResponse,
    BarResponse,
    MarketStatusResponse,
    MarketUniverseResponse,
    SymbolLookupResponse,
    StreamPreviewResponse,
)
from app.utils.serializers import to_float

router = APIRouter(prefix="/market-data")


def backfill_market_data(*args, **kwargs):
    from app.services.market_data_service import backfill_market_data as service

    return service(*args, **kwargs)


def get_bars(*args, **kwargs):
    from app.services.market_data_service import get_bars as service

    return service(*args, **kwargs)


def get_or_fetch_bars(*args, **kwargs):
    from app.services.market_data_service import get_or_fetch_bars as service

    return service(*args, **kwargs)


def get_market_status(*args, **kwargs):
    from app.services.market_data_service import get_market_status as service

    return service(*args, **kwargs)


def list_tracked_symbols(*args, **kwargs):
    from app.services.market_data_service import list_tracked_symbols as service

    return service(*args, **kwargs)


def list_market_universe(*args, **kwargs):
    from app.services.market_data_service import list_market_universe as service

    return service(*args, **kwargs)


def preview_stream(*args, **kwargs):
    from app.services.polygon.stream import preview_stream as service

    return service(*args, **kwargs)


@router.post("/backfill", response_model=BackfillResponse)
def backfill(
    payload: BackfillRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> BackfillResponse:
    try:
        inserted, source = backfill_market_data(
            session,
            request.app.state.settings,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            start=payload.start,
            end=payload.end,
            source=payload.source,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return BackfillResponse(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        inserted=inserted,
        source=source,
        start=payload.start,
        end=payload.end,
    )


@router.get("/bars", response_model=list[BarResponse])
def list_bars(
    request: Request,
    symbol: str,
    timeframe: str = "1min",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=500, le=5000),
    refresh: bool = False,
    session: Session = Depends(get_db_session),
) -> list[BarResponse]:
    try:
        rows = get_or_fetch_bars(
            session,
            request.app.state.settings,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
            refresh=refresh,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        BarResponse(
            symbol=ticker,
            timeframe=row.timeframe,
            timestamp=row.timestamp,
            open=to_float(row.open) or 0.0,
            high=to_float(row.high) or 0.0,
            low=to_float(row.low) or 0.0,
            close=to_float(row.close) or 0.0,
            volume=row.volume,
            vwap=to_float(row.vwap),
            trades_count=row.trades_count,
        )
        for row, ticker in rows
    ]


@router.get("/universe", response_model=MarketUniverseResponse)
def universe(
    request: Request,
    locale: str = Query(default="us"),
    query: str | None = Query(default=None),
    exchange: str | None = Query(default=None),
    active_only: bool = True,
    limit: int = Query(default=48, le=100),
    cursor: str | None = Query(default=None),
    security_type: str = Query(default="CS"),
    currency: str | None = Query(default=None),
    include_quotes: bool = True,
    session: Session = Depends(get_db_session),
) -> MarketUniverseResponse:
    page = list_market_universe(
        session,
        request.app.state.settings,
        locale=locale,
        query=query,
        exchange=exchange,
        active_only=active_only,
        limit=limit,
        cursor=cursor,
        security_type=security_type,
        currency=currency,
        include_quotes=include_quotes,
    )
    return MarketUniverseResponse(
        items=[
            SymbolLookupResponse(
                ticker=item.ticker,
                name=item.name,
                exchange=item.exchange,
                asset_type=item.asset_type,
                is_active=item.is_active,
                market=item.market,
                primary_exchange=item.primary_exchange,
                security_type=item.security_type,
                currency=item.currency,
                round_lot_size=item.round_lot_size,
                minimum_order_size=item.minimum_order_size,
                last_updated_utc=item.last_updated_utc,
                last_price=item.last_price,
                change=item.change,
                change_percent=item.change_percent,
                quote_timestamp=item.quote_timestamp,
                quote_source=item.quote_source,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
        source=page.source,
        as_of=page.as_of,
    )


@router.get("/symbols", response_model=list[SymbolLookupResponse])
def list_symbols(
    exchange: str | None = Query(default=None),
    query: str | None = Query(default=None),
    active_only: bool = True,
    limit: int = Query(default=250, le=1000),
    session: Session = Depends(get_db_session),
) -> list[SymbolLookupResponse]:
    return [
        SymbolLookupResponse(
            ticker=row.ticker,
            name=row.name,
            exchange=row.exchange,
            asset_type=row.asset_type,
            is_active=row.is_active,
        )
        for row in list_tracked_symbols(
            session,
            exchange=exchange,
            query=query,
            active_only=active_only,
            limit=limit,
        )
    ]


@router.get("/stream/preview", response_model=StreamPreviewResponse)
def stream_preview(
    symbol: str,
    timeframe: str = "1min",
    points: int = Query(default=20, le=100),
) -> StreamPreviewResponse:
    try:
        bars = preview_stream([symbol.upper()], timeframe=timeframe, points=points)[symbol.upper()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamPreviewResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        source="synthetic-preview",
        bars=[
            BarResponse(
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                timestamp=bar.timestamp,
                open=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                close=float(bar.close),
                volume=bar.volume,
                vwap=float(bar.vwap) if bar.vwap is not None else None,
                trades_count=bar.trades_count,
            )
            for bar in bars
        ],
    )


@router.get("/market-status", response_model=MarketStatusResponse)
def market_status(
    request: Request,
    exchange: str = Query(default="US", min_length=1),
) -> MarketStatusResponse:
    try:
        status, provider = get_market_status(request.app.state.settings, exchange=exchange.upper())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return MarketStatusResponse(
        exchange=status.exchange,
        holiday=status.holiday,
        is_open=status.is_open,
        session=status.session,
        timezone=status.timezone_name,
        timestamp=status.timestamp,
        provider=provider,
    )
