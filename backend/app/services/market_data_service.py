from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

import numpy as np
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market_bar import MarketDataBar
from app.models.symbol import Symbol
from app.services.eodhd.client import EodhdClient
from app.services.finnhub.client import FinnhubClient
from app.services.finnhub.historical import normalize_finnhub_candles
from app.services.finnhub.market import (
    FinnhubMarketStatus,
    fetch_market_status as fetch_finnhub_market_status,
    fetch_quote as fetch_finnhub_quote,
)
from app.services.ibkr.client import IbkrMarketDataClient, infer_ibkr_currency, infer_ibkr_primary_exchange
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


@dataclass(slots=True)
class LiveQuote:
    ticker: str
    last_price: float
    change: float | None
    change_percent: float | None
    timestamp: datetime
    source: str
    name: str | None = None
    exchange: str | None = None
    primary_exchange: str | None = None
    currency: str | None = None


@dataclass(slots=True)
class MarketUniverseItem:
    ticker: str
    name: str | None
    exchange: str | None
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


@dataclass(slots=True)
class MarketUniversePage:
    items: list[MarketUniverseItem]
    next_cursor: str | None
    source: str
    as_of: datetime


@dataclass(slots=True)
class CachedUniversePage:
    page: MarketUniversePage
    expires_at: datetime


@dataclass(slots=True)
class CachedQuote:
    quote: LiveQuote
    expires_at: datetime


_UNIVERSE_CACHE_TTL_SECONDS = 90
_QUOTE_CACHE_TTL_SECONDS = 45
_UNIVERSE_CACHE: dict[tuple[object, ...], CachedUniversePage] = {}
_QUOTE_CACHE: dict[str, CachedQuote] = {}
_EODHD_EUROPE_EXCHANGES = ("PA", "XETRA", "MC", "AS", "BR", "VI", "LSE")
_EODHD_LOCAL_SUFFIX_TO_EXCHANGE = {
    "AS": "AS",
    "BR": "BR",
    "DE": "XETRA",
    "LS": "LSE",
    "MC": "MC",
    "PA": "PA",
    "SW": "SW",
    "VI": "VI",
}
_EODHD_EXCHANGE_TO_LOCAL_SUFFIX = {value: key for key, value in _EODHD_LOCAL_SUFFIX_TO_EXCHANGE.items()}


def _is_europe_request(*, locale: str, currency: str | None) -> bool:
    normalized_locale = (locale or "").strip().lower()
    normalized_currency = (currency or "").strip().upper()
    return normalized_currency == "EUR" or normalized_locale in {"eu", "europe", "global"}


def _local_symbol_to_eodhd_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        return normalized
    if "." not in normalized:
        return f"{normalized}.US"

    code, suffix = normalized.rsplit(".", 1)
    exchange = _EODHD_LOCAL_SUFFIX_TO_EXCHANGE.get(suffix)
    if exchange:
        return f"{code}.{exchange}"
    return normalized


def _eodhd_to_local_symbol(*, code: str, exchange: str) -> str:
    normalized_code = code.strip().upper()
    normalized_exchange = exchange.strip().upper()
    if normalized_exchange == "US":
        return normalized_code
    suffix = _EODHD_EXCHANGE_TO_LOCAL_SUFFIX.get(normalized_exchange, normalized_exchange)
    return f"{normalized_code}.{suffix}"


def _coerce_float(value: object) -> float | None:
    if value in {None, "", "NA"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_eodhd_asset_type(asset_type: str | None) -> str:
    normalized = (asset_type or "").strip().lower()
    if normalized == "etf":
        return "etf"
    return "equity"


def _matches_security_type(*, item_type: str | None, security_type: str | None) -> bool:
    normalized_security_type = (security_type or "").strip().upper()
    if not normalized_security_type or normalized_security_type == "ALL":
        return True
    normalized_item_type = (item_type or "").strip().lower()
    if normalized_security_type == "CS":
        return normalized_item_type == "common stock"
    if normalized_security_type == "ETF":
        return normalized_item_type == "etf"
    return True


def _build_eodhd_market_item(payload: dict[str, object]) -> MarketUniverseItem | None:
    code = str(payload.get("Code") or payload.get("code") or "").strip().upper()
    exchange = str(payload.get("Exchange") or payload.get("exchange") or "").strip().upper()
    if not code or not exchange:
        return None

    local_ticker = _eodhd_to_local_symbol(code=code, exchange=exchange)
    asset_label = str(payload.get("Type") or payload.get("type") or "Common Stock")
    asset_type = _normalize_eodhd_asset_type(asset_label)
    currency = str(payload.get("Currency") or payload.get("currency") or "").strip().upper() or None
    name = str(payload.get("Name") or payload.get("name") or local_ticker).strip() or local_ticker
    return MarketUniverseItem(
        ticker=local_ticker,
        name=name,
        exchange=exchange,
        asset_type=asset_type,
        is_active=True,
        market="stocks",
        primary_exchange=exchange,
        security_type="ETF" if asset_type == "etf" else "CS",
        currency=currency,
        round_lot_size=_default_round_lot_size(asset_type),
        minimum_order_size=1,
    )


def ensure_symbol(session: Session, ticker: str) -> Symbol:
    symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker.upper()))
    if symbol is not None:
        return symbol

    symbol = Symbol(
        ticker=ticker.upper(),
        name=ticker.upper(),
        exchange=infer_ibkr_primary_exchange(ticker) or "SMART",
    )
    session.add(symbol)
    session.commit()
    session.refresh(symbol)
    return symbol


def _universe_cache_key(
    *,
    locale: str,
    query: str | None,
    exchange: str | None,
    active_only: bool,
    limit: int,
    cursor: str | None,
    security_type: str | None,
    currency: str | None,
    include_quotes: bool,
) -> tuple[object, ...]:
    return (
        locale.strip().lower(),
        (query or "").strip().upper() or None,
        (exchange or "").strip().upper() or None,
        active_only,
        limit,
        cursor,
        (security_type or "").strip().upper() or None,
        (currency or "").strip().upper() or None,
        include_quotes,
    )


def _clone_universe_page(page: MarketUniversePage, *, source: str | None = None) -> MarketUniversePage:
    return MarketUniversePage(
        items=[MarketUniverseItem(**asdict(item)) for item in page.items],
        next_cursor=page.next_cursor,
        source=source or page.source,
        as_of=page.as_of,
    )


def _get_cached_universe_page(cache_key: tuple[object, ...]) -> MarketUniversePage | None:
    cached_entry = _UNIVERSE_CACHE.get(cache_key)
    if cached_entry is None:
        return None

    if cached_entry.expires_at <= datetime.now(timezone.utc):
        _UNIVERSE_CACHE.pop(cache_key, None)
        return None

    return _clone_universe_page(cached_entry.page, source=f"{cached_entry.page.source}-cache")


def _store_universe_page(cache_key: tuple[object, ...], page: MarketUniversePage) -> None:
    _UNIVERSE_CACHE[cache_key] = CachedUniversePage(
        page=_clone_universe_page(page),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_UNIVERSE_CACHE_TTL_SECONDS),
    )


def _normalize_asset_type(security_type: str | None) -> str:
    normalized = (security_type or "").upper()
    if normalized == "ETF":
        return "etf"
    return "equity"


def _default_round_lot_size(asset_type: str) -> int:
    return 100 if asset_type in {"equity", "etf"} else 1


def _parse_cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(cursor))
    except ValueError:
        return 0


def _next_cursor_offset(*, offset: int, total_items: int, limit: int) -> str | None:
    next_offset = offset + limit
    return str(next_offset) if next_offset < total_items else None


def _item_matches_filters(
    item: MarketUniverseItem,
    *,
    query: str | None,
    exchange: str | None,
    currency: str | None,
) -> bool:
    normalized_query = query.strip().upper() if query else None
    normalized_exchange = exchange.strip().upper() if exchange else None
    normalized_currency = currency.strip().upper() if currency else None

    if normalized_query:
        haystack = " ".join(
            [
                item.ticker,
                item.name or "",
                item.exchange or "",
                item.primary_exchange or "",
            ]
        ).upper()
        if normalized_query not in haystack:
            return False

    if normalized_exchange and normalized_exchange != "ALL":
        exchange_candidates = {
            (item.exchange or "").upper(),
            (item.primary_exchange or "").upper(),
        }
        if normalized_exchange not in exchange_candidates:
            return False

    if normalized_currency and (item.currency or "").upper() != normalized_currency:
        return False

    return True


def _build_watchlist_universe(
    session: Session,
    settings: Settings,
    *,
    query: str | None,
    exchange: str | None,
    active_only: bool,
    currency: str | None,
) -> list[MarketUniverseItem]:
    tracked_rows = {
        row.ticker.upper(): row
        for row in list_tracked_symbols(session, exchange=None, query=None, active_only=active_only, limit=500)
    }
    ordered_tickers: list[str] = []
    for ticker in [*settings.default_symbols, *tracked_rows.keys()]:
        normalized = ticker.upper()
        if normalized not in ordered_tickers:
            ordered_tickers.append(normalized)

    items: list[MarketUniverseItem] = []
    for ticker in ordered_tickers:
        row = tracked_rows.get(ticker)
        inferred_exchange = infer_ibkr_primary_exchange(ticker) or row.exchange if row else infer_ibkr_primary_exchange(ticker)
        item = MarketUniverseItem(
            ticker=ticker,
            name=row.name if row else ticker,
            exchange=row.exchange if row and row.exchange else inferred_exchange,
            asset_type=row.asset_type if row else "equity",
            is_active=row.is_active if row else True,
            market="stocks",
            primary_exchange=inferred_exchange or (row.exchange if row else None),
            security_type="CS",
            currency=infer_ibkr_currency(ticker),
            round_lot_size=_default_round_lot_size(row.asset_type if row else "equity"),
            minimum_order_size=1,
        )
        if _item_matches_filters(item, query=query, exchange=exchange, currency=currency):
            items.append(item)

    return items


def _apply_quote_to_item(item: MarketUniverseItem, quote: LiveQuote | None) -> MarketUniverseItem:
    if quote is None:
        return item
    return MarketUniverseItem(
        ticker=item.ticker,
        name=quote.name or item.name,
        exchange=quote.exchange or item.exchange,
        asset_type=item.asset_type,
        is_active=item.is_active,
        market=item.market,
        primary_exchange=quote.primary_exchange or item.primary_exchange,
        security_type=item.security_type,
        currency=quote.currency or item.currency,
        round_lot_size=item.round_lot_size,
        minimum_order_size=item.minimum_order_size,
        last_updated_utc=quote.timestamp,
        last_price=quote.last_price,
        change=quote.change,
        change_percent=quote.change_percent,
        quote_timestamp=quote.timestamp,
        quote_source=quote.source,
    )


def search_ibkr_market_summaries(
    settings: Settings,
    *,
    query: str,
    currency: str,
    limit: int,
) -> list[MarketUniverseItem]:
    with IbkrMarketDataClient(settings) as client:
        summaries = client.search_stocks(query, currency=currency, limit=limit)
    return [
        MarketUniverseItem(
            ticker=summary.ticker,
            name=summary.name,
            exchange=summary.exchange,
            asset_type="equity",
            is_active=True,
            market="stocks",
            primary_exchange=summary.primary_exchange,
            security_type="CS",
            currency=summary.currency,
            round_lot_size=_default_round_lot_size("equity"),
            minimum_order_size=1,
        )
        for summary in summaries
    ]


def search_eodhd_market_summaries(
    settings: Settings,
    *,
    query: str,
    locale: str,
    currency: str | None,
    security_type: str | None,
    limit: int,
) -> list[MarketUniverseItem]:
    payload = EodhdClient(settings).search(query=query, limit=limit)
    wants_europe = _is_europe_request(locale=locale, currency=currency)
    items: list[MarketUniverseItem] = []
    for row in payload:
        item = _build_eodhd_market_item(row)
        if item is None:
            continue
        if wants_europe and (item.exchange or "").upper() not in _EODHD_EUROPE_EXCHANGES:
            continue
        if currency and (item.currency or "").upper() != currency.upper():
            continue
        if not _matches_security_type(item_type=str(row.get("Type") or row.get("type") or ""), security_type=security_type):
            continue
        items.append(item)
    items.sort(key=lambda item: ((item.exchange or ""), item.ticker))
    return items[:limit]


def list_eodhd_market_universe(
    settings: Settings,
    *,
    locale: str,
    exchange: str | None,
    currency: str | None,
    security_type: str | None,
) -> list[MarketUniverseItem]:
    if not _is_europe_request(locale=locale, currency=currency):
        return []

    exchanges = [exchange.strip().upper()] if exchange else list(_EODHD_EUROPE_EXCHANGES)
    client = EodhdClient(settings)
    items_by_ticker: dict[str, MarketUniverseItem] = {}
    successful_fetches = 0

    for exchange_code in exchanges:
        rows = client.list_exchange_symbols(exchange=exchange_code)
        successful_fetches += 1
        for row in rows:
            item = _build_eodhd_market_item(row)
            if item is None:
                continue
            if currency and (item.currency or "").upper() != currency.upper():
                continue
            if not _matches_security_type(item_type=str(row.get("Type") or row.get("type") or ""), security_type=security_type):
                continue
            items_by_ticker.setdefault(item.ticker, item)

    if not successful_fetches:
        raise RuntimeError("EODHD did not return any European exchange lists.")

    items = sorted(items_by_ticker.values(), key=lambda item: ((item.exchange or ""), item.ticker))
    return items


def fetch_eodhd_eod_bars(
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[NormalizedBar]:
    payload = EodhdClient(settings).get_eod_bars(
        symbol=_local_symbol_to_eodhd_symbol(symbol),
        start=ensure_utc(start),
        end=ensure_utc(end),
    )
    bars: list[NormalizedBar] = []
    for row in payload:
        date_value = str(row.get("date") or "").strip()
        if not date_value:
            continue
        timestamp = ensure_utc(datetime.fromisoformat(f"{date_value}T00:00:00+00:00"))
        open_value = _coerce_float(row.get("open"))
        high_value = _coerce_float(row.get("high"))
        low_value = _coerce_float(row.get("low"))
        close_value = _coerce_float(row.get("close"))
        if None in {open_value, high_value, low_value, close_value}:
            continue
        volume_value = int(_coerce_float(row.get("volume")) or 0)
        bars.append(
            NormalizedBar(
                symbol=symbol.upper(),
                timeframe=timeframe,
                timestamp=timestamp,
                open=Decimal(f"{open_value:.6f}"),
                high=Decimal(f"{high_value:.6f}"),
                low=Decimal(f"{low_value:.6f}"),
                close=Decimal(f"{close_value:.6f}"),
                volume=volume_value,
                vwap=None,
                trades_count=None,
            )
        )
    return bars


def fetch_ibkr_historical_bars(
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[NormalizedBar]:
    with IbkrMarketDataClient(settings) as client:
        ibkr_bars = client.fetch_historical_bars(
            symbol.upper(),
            timeframe=timeframe,
            start=ensure_utc(start),
            end=ensure_utc(end),
        )
    return [
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
        for bar in ibkr_bars
    ]


def fetch_live_quotes(settings: Settings, tickers: list[str]) -> dict[str, LiveQuote]:
    normalized_tickers = list(dict.fromkeys(ticker.upper() for ticker in tickers if ticker.strip()))
    if not normalized_tickers:
        return {}

    quotes: dict[str, LiveQuote] = {}
    now = datetime.now(timezone.utc)
    pending_tickers: list[str] = []
    for normalized_ticker in normalized_tickers:
        cached_quote = _QUOTE_CACHE.get(normalized_ticker)
        if cached_quote is not None and cached_quote.expires_at > now:
            quotes[normalized_ticker] = cached_quote.quote
            continue
        pending_tickers.append(normalized_ticker)

    if not pending_tickers:
        return quotes

    if settings.eodhd_api_token:
        request_symbols = {_local_symbol_to_eodhd_symbol(ticker): ticker for ticker in pending_tickers}
        try:
            payload = EodhdClient(settings).get_real_time_quotes(symbols=list(request_symbols))
        except RuntimeError:
            payload = []

        for row in payload:
            code = str(row.get("code") or "").strip().upper()
            if not code:
                continue
            requested_ticker = request_symbols.get(code)
            if requested_ticker is None:
                if "." in code:
                    base_code, exchange = code.rsplit(".", 1)
                    requested_ticker = _eodhd_to_local_symbol(code=base_code, exchange=exchange)
                else:
                    requested_ticker = code

            last_price = _coerce_float(row.get("close"))
            if last_price is None:
                continue

            timestamp_raw = row.get("timestamp")
            timestamp = (
                datetime.fromtimestamp(int(timestamp_raw), tz=timezone.utc)
                if isinstance(timestamp_raw, (int, float)) or str(timestamp_raw).isdigit()
                else now
            )
            live_quote = LiveQuote(
                ticker=requested_ticker.upper(),
                last_price=last_price,
                change=_coerce_float(row.get("change")),
                change_percent=_coerce_float(row.get("change_p")),
                timestamp=timestamp,
                source="eodhd",
                exchange=code.rsplit(".", 1)[1] if "." in code else "US",
                primary_exchange=code.rsplit(".", 1)[1] if "." in code else "US",
                currency=infer_ibkr_currency(requested_ticker),
            )
            for cache_key in {requested_ticker.upper(), code}:
                quotes[cache_key] = live_quote
                _QUOTE_CACHE[cache_key] = CachedQuote(
                    quote=live_quote,
                    expires_at=now + timedelta(seconds=_QUOTE_CACHE_TTL_SECONDS),
                )

        pending_tickers = [ticker for ticker in pending_tickers if ticker not in quotes]

    if not pending_tickers or not settings.ibkr_host:
        return quotes

    try:
        with IbkrMarketDataClient(settings) as client:
            for normalized_ticker in pending_tickers:
                try:
                    quote = client.fetch_quote(normalized_ticker)
                except Exception:
                    continue

                previous_close = quote.previous_close
                if previous_close in {None, 0.0}:
                    change = None
                    change_percent = None
                else:
                    change = quote.last_price - previous_close
                    change_percent = (change / previous_close) * 100

                live_quote = LiveQuote(
                    ticker=quote.ticker.upper(),
                    last_price=float(quote.last_price),
                    change=change,
                    change_percent=change_percent,
                    timestamp=quote.timestamp,
                    source=quote.source,
                    name=quote.contract.name,
                    exchange=quote.contract.exchange,
                    primary_exchange=quote.contract.primary_exchange,
                    currency=quote.contract.currency,
                )
                for cache_key in {normalized_ticker, live_quote.ticker}:
                    quotes[cache_key] = live_quote
                    _QUOTE_CACHE[cache_key] = CachedQuote(
                        quote=live_quote,
                        expires_at=now + timedelta(seconds=_QUOTE_CACHE_TTL_SECONDS),
                    )
    except RuntimeError:
        return quotes

    return quotes


def list_market_universe(
    session: Session,
    settings: Settings,
    *,
    locale: str = "us",
    query: str | None = None,
    exchange: str | None = None,
    active_only: bool = True,
    limit: int = 48,
    cursor: str | None = None,
    security_type: str | None = "CS",
    currency: str | None = None,
    include_quotes: bool = True,
) -> MarketUniversePage:
    normalized_locale = (locale or "us").strip().lower() or "us"
    normalized_currency = (currency or "").strip().upper() or None
    europe_request = _is_europe_request(locale=normalized_locale, currency=normalized_currency)
    offset = _parse_cursor_offset(cursor)
    cache_key = _universe_cache_key(
        locale=normalized_locale,
        query=query,
        exchange=exchange,
        active_only=active_only,
        limit=limit,
        cursor=cursor,
        security_type=security_type,
        currency=normalized_currency,
        include_quotes=include_quotes,
    )
    cached_page = _get_cached_universe_page(cache_key)
    if cached_page is not None:
        return cached_page

    as_of = datetime.now(timezone.utc)
    source = "local-watchlist"

    if query and query.strip():
        if settings.eodhd_api_token:
            try:
                items = search_eodhd_market_summaries(
                    settings,
                    query=query,
                    locale=normalized_locale,
                    currency=normalized_currency,
                    security_type=security_type,
                    limit=max(offset + limit, limit * 2, 50),
                )
            except RuntimeError as exc:
                log_event(
                    session,
                    level="WARNING",
                    source="market_data",
                    event_type="market_universe_fallback",
                    message="Falling back after EODHD symbol-search failure.",
                    context={"query": query, "exchange": exchange, "reason": str(exc)},
                )
                items = _build_watchlist_universe(
                    session,
                    settings,
                    query=query,
                    exchange=exchange,
                    active_only=active_only,
                    currency=normalized_currency,
                )
                source = "eodhd-search-fallback"
            else:
                source = "eodhd-search"
        elif settings.ibkr_host and europe_request:
            try:
                items = search_ibkr_market_summaries(
                    settings,
                    query=query,
                    currency=normalized_currency or "EUR",
                    limit=max(offset + limit, limit * 2, 50),
                )
            except RuntimeError as exc:
                log_event(
                    session,
                    level="WARNING",
                    source="market_data",
                    event_type="market_universe_fallback",
                    message="Falling back after IBKR symbol-search failure.",
                    context={"query": query, "exchange": exchange, "reason": str(exc)},
                )
                items = _build_watchlist_universe(
                    session,
                    settings,
                    query=query,
                    exchange=exchange,
                    active_only=active_only,
                    currency=normalized_currency,
                )
                source = "ibkr-search-fallback"
            else:
                source = "ibkr-symbol-search"
        else:
            items = _build_watchlist_universe(
                session,
                settings,
                query=query,
                exchange=exchange,
                active_only=active_only,
                currency=normalized_currency,
            )
            source = "eodhd-search-fallback" if europe_request else "local-search"
        items = [
            item
            for item in items
            if _item_matches_filters(item, query=None, exchange=exchange, currency=normalized_currency)
        ]
    else:
        if europe_request and settings.eodhd_api_token:
            try:
                items = list_eodhd_market_universe(
                    settings,
                    locale=normalized_locale,
                    exchange=exchange,
                    currency=normalized_currency,
                    security_type=security_type,
                )
            except RuntimeError as exc:
                log_event(
                    session,
                    level="WARNING",
                    source="market_data",
                    event_type="market_universe_fallback",
                    message="Falling back after EODHD exchange-list failure.",
                    context={"exchange": exchange, "reason": str(exc)},
                )
                items = _build_watchlist_universe(
                    session,
                    settings,
                    query=query,
                    exchange=exchange,
                    active_only=active_only,
                    currency=normalized_currency,
                )
                source = "eodhd-watchlist-fallback"
            else:
                source = "eodhd-europe-exchanges"
        else:
            items = _build_watchlist_universe(
                session,
                settings,
                query=query,
                exchange=exchange,
                active_only=active_only,
                currency=normalized_currency,
            )
            if europe_request:
                source = "eodhd-watchlist-fallback"

    total_items = len(items)
    page_items = items[offset : offset + limit]
    if include_quotes and page_items:
        quote_lookup = fetch_live_quotes(settings, [item.ticker for item in page_items])
        if not quote_lookup and source in {"eodhd-europe-exchanges", "eodhd-search", "ibkr-symbol-search"}:
            source = f"{source}-fallback"
        page_items = [_apply_quote_to_item(item, quote_lookup.get(item.ticker.upper())) for item in page_items]

    page = MarketUniversePage(
        items=page_items,
        next_cursor=_next_cursor_offset(offset=offset, total_items=total_items, limit=limit),
        source=source,
        as_of=as_of,
    )
    _store_universe_page(cache_key, page)
    return page


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


def resolve_source(
    settings: Settings,
    source: str,
    *,
    timeframe: str,
) -> Literal["eodhd", "ibkr", "polygon", "finnhub", "synthetic"]:
    normalized = source.lower().strip()
    if normalized == "eodhd":
        if not settings.eodhd_api_token:
            raise RuntimeError("Requested EODHD source but EODHD_API_TOKEN is not configured.")
        return "eodhd"
    if normalized == "ibkr":
        if not settings.ibkr_host:
            raise RuntimeError("Requested IBKR source but IBKR_HOST is not configured.")
        return "ibkr"
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
    if timeframe.lower() == "1day" and settings.eodhd_api_token:
        return "eodhd"
    return "ibkr" if settings.ibkr_host else "synthetic"


def fetch_historical_bars(
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    source: str,
) -> tuple[list[NormalizedBar], str]:
    selected_source = resolve_source(settings, source, timeframe=timeframe)
    if selected_source == "eodhd":
        if timeframe.lower() != "1day":
            raise RuntimeError(
                "EODHD intraday candles are not enabled for this token. Use timeframe=1day or keep IBKR for intraday bars."
            )
        return (
            fetch_eodhd_eod_bars(
                settings,
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            ),
            "eodhd",
        )
    if selected_source == "ibkr":
        return (
            fetch_ibkr_historical_bars(
                settings,
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            ),
            "ibkr",
        )
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
    existing_by_timestamp = {ensure_utc(row.timestamp): row for row in existing_rows}

    inserted = 0
    for bar in bars:
        bar_timestamp = ensure_utc(bar.timestamp)
        row = existing_by_timestamp.get(bar_timestamp)
        if row is None:
            row = MarketDataBar(
                symbol_id=symbol_row.id,
                timeframe=timeframe,
                timestamp=bar_timestamp,
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
    if settings.eodhd_api_token:
        sources.append("eodhd")
    if settings.ibkr_host:
        sources.append("ibkr")
    if settings.polygon_api_key:
        sources.append("polygon")
    if settings.finnhub_api_key:
        sources.append("finnhub")
    sources.append("synthetic")
    return sources


def list_tracked_symbols(
    session: Session,
    *,
    exchange: str | None = None,
    query: str | None = None,
    active_only: bool = True,
    limit: int = 250,
) -> list[Symbol]:
    statement = select(Symbol)

    if active_only:
        statement = statement.where(Symbol.is_active.is_(True))

    normalized_exchange = exchange.strip().upper() if exchange else None
    if normalized_exchange and normalized_exchange != "ALL":
        statement = statement.where(func.upper(Symbol.exchange) == normalized_exchange)

    normalized_query = query.strip().upper() if query else None
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.where(
            or_(
                func.upper(Symbol.ticker).like(pattern),
                func.upper(func.coalesce(Symbol.name, "")).like(pattern),
                func.upper(func.coalesce(Symbol.exchange, "")).like(pattern),
            )
        )

    statement = statement.order_by(Symbol.exchange.asc(), Symbol.ticker.asc()).limit(limit)
    return list(session.scalars(statement))


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

    if start is None and end is None:
        rows = list(session.scalars(query.order_by(desc(MarketDataBar.timestamp)).limit(limit)))
        rows.reverse()
        return [(row, symbol_row.ticker) for row in rows]

    query = query.order_by(MarketDataBar.timestamp.asc()).limit(limit)
    return [(row, symbol_row.ticker) for row in session.scalars(query)]


def _recent_fetch_window(*, timeframe: str, limit: int) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if timeframe.lower() == "1day":
        window_days = max(limit * 2, 180)
        return now - timedelta(days=window_days), now

    minutes = timeframe_to_minutes(timeframe)
    approximate_session_span = max((minutes * limit) / 390, 1)
    window_days = max(int(approximate_session_span * 7) + 7, 10)
    return now - timedelta(days=window_days), now


def _refresh_fetch_window(*, timeframe: str, limit: int) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if timeframe.lower() == "1day":
        window_days = max(limit + 5, 30)
        return now - timedelta(days=window_days), now

    minutes = timeframe_to_minutes(timeframe)
    approximate_session_span = max((minutes * limit) / 390, 1)
    window_days = max(int(approximate_session_span) + 2, 2)
    return now - timedelta(days=window_days), now


def get_or_fetch_bars(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
    refresh: bool = False,
) -> list[tuple[MarketDataBar, str]]:
    rows = get_bars(session, symbol=symbol, timeframe=timeframe, start=start, end=end, limit=limit)
    if start is not None or end is not None:
        return rows

    if refresh:
        fetch_start, fetch_end = _refresh_fetch_window(timeframe=timeframe, limit=limit)
        try:
            bars, _ = fetch_historical_bars(
                settings,
                symbol=symbol,
                timeframe=timeframe,
                start=fetch_start,
                end=fetch_end,
                source="auto",
            )
            upsert_bars(session, symbol=symbol, timeframe=timeframe, bars=bars)
        except RuntimeError as exc:
            log_event(
                session,
                level="WARNING",
                source="market_data",
                event_type="market_refresh_fallback",
                message=f"Falling back after refresh failure for {symbol.upper()} {timeframe}",
                context={"symbol": symbol.upper(), "timeframe": timeframe, "reason": str(exc)},
            )
            return rows
        return get_bars(session, symbol=symbol, timeframe=timeframe, start=None, end=None, limit=limit)

    if rows:
        return rows

    fetch_start, fetch_end = _recent_fetch_window(timeframe=timeframe, limit=limit)
    try:
        bars, _ = fetch_historical_bars(
            settings,
            symbol=symbol,
            timeframe=timeframe,
            start=fetch_start,
            end=fetch_end,
            source="auto",
        )
        upsert_bars(session, symbol=symbol, timeframe=timeframe, bars=bars)
    except RuntimeError as exc:
        log_event(
            session,
            level="WARNING",
            source="market_data",
            event_type="market_fetch_fallback",
            message=f"Falling back to preview because provider bars are unavailable for {symbol.upper()} {timeframe}",
            context={"symbol": symbol.upper(), "timeframe": timeframe, "reason": str(exc)},
        )
        return rows
    return get_bars(session, symbol=symbol, timeframe=timeframe, start=None, end=None, limit=limit)


def latest_price(session: Session, settings: Settings, symbol: str, timeframe: str = "1min") -> float:
    symbol_row = ensure_symbol(session, symbol)
    latest_bar = session.scalar(
        select(MarketDataBar)
        .where(and_(MarketDataBar.symbol_id == symbol_row.id, MarketDataBar.timeframe == timeframe))
        .order_by(MarketDataBar.timestamp.desc())
        .limit(1)
    )
    if latest_bar is None:
        if settings.eodhd_api_token:
            try:
                quote = fetch_live_quotes(settings, [symbol]).get(symbol.upper())
                if quote is not None:
                    return float(quote.last_price)
            except Exception:
                pass
        if settings.ibkr_host:
            try:
                with IbkrMarketDataClient(settings) as client:
                    return float(client.fetch_quote(symbol).last_price)
            except Exception:
                pass
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
