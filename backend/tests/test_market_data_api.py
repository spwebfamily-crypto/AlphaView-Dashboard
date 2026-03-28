from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.market_bar import MarketDataBar
from app.models.symbol import Symbol
from app.services.polygon.stream import preview_stream
from app.services.market_data_service import NormalizedBar
from app.services.polygon.historical import PolygonAggregateBar
from app.services.finnhub.historical import FinnhubCandleBar
from app.services.finnhub.market import FinnhubMarketStatus
from app.services.market_data_service import MarketUniverseItem, MarketUniversePage, ensure_symbol, list_market_universe


def test_market_data_backfill_and_query(authenticated_client) -> None:
    response = authenticated_client.post(
        "/api/v1/market-data/backfill",
        json={
            "symbol": "AAPL",
            "timeframe": "1min",
            "start": "2026-01-05T14:30:00Z",
            "end": "2026-01-06T20:00:00Z",
            "source": "synthetic",
        },
    )
    assert response.status_code == 200
    assert response.json()["inserted"] > 0

    bars_response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "AAPL", "timeframe": "1min", "limit": 25},
    )
    assert bars_response.status_code == 200
    payload = bars_response.json()
    assert len(payload) > 0
    assert payload[0]["symbol"] == "AAPL"


def test_market_data_backfill_supports_finnhub_source(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.finnhub_api_key = "test-token"

    def fake_finnhub_bars(*args, **kwargs) -> list[FinnhubCandleBar]:
        return [
            FinnhubCandleBar(
                timestamp=datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc),
                open=Decimal("210.10"),
                high=Decimal("211.25"),
                low=Decimal("209.90"),
                close=Decimal("210.80"),
                volume=125000,
            ),
            FinnhubCandleBar(
                timestamp=datetime(2026, 1, 5, 14, 31, tzinfo=timezone.utc),
                open=Decimal("210.80"),
                high=Decimal("211.40"),
                low=Decimal("210.55"),
                close=Decimal("211.10"),
                volume=119500,
            ),
        ]

    monkeypatch.setattr("app.services.market_data_service.normalize_finnhub_candles", fake_finnhub_bars)

    response = authenticated_client.post(
        "/api/v1/market-data/backfill",
        json={
            "symbol": "MSFT",
            "timeframe": "1min",
            "start": "2026-01-05T14:30:00Z",
            "end": "2026-01-05T15:00:00Z",
            "source": "finnhub",
        },
    )
    assert response.status_code == 200
    assert response.json()["source"] == "finnhub"
    assert response.json()["inserted"] == 2


def test_market_data_query_auto_fetches_ibkr_when_store_is_empty(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.ibkr_host = "127.0.0.1"

    def fake_ibkr_bars(*args, **kwargs) -> list[NormalizedBar]:
        return [
            NormalizedBar(
                symbol="AAPL",
                timeframe="1min",
                timestamp=datetime(2026, 3, 26, 14, 30, tzinfo=timezone.utc),
                open=Decimal("170.10"),
                high=Decimal("171.25"),
                low=Decimal("169.95"),
                close=Decimal("170.85"),
                volume=4500000,
                vwap=None,
                trades_count=None,
            ),
            NormalizedBar(
                symbol="AAPL",
                timeframe="1min",
                timestamp=datetime(2026, 3, 26, 14, 31, tzinfo=timezone.utc),
                open=Decimal("170.85"),
                high=Decimal("171.40"),
                low=Decimal("170.60"),
                close=Decimal("171.20"),
                volume=4250000,
                vwap=None,
                trades_count=None,
            ),
        ]

    monkeypatch.setattr("app.services.market_data_service.fetch_ibkr_historical_bars", fake_ibkr_bars)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "AAPL", "timeframe": "1min", "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["symbol"] == "AAPL"
    assert payload[0]["close"] == 170.85


def test_market_data_query_auto_fetches_eodhd_daily_bars_when_configured(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.eodhd_api_token = "test-token"

    def fake_eodhd_bars(*args, **kwargs) -> list[NormalizedBar]:
        return [
            NormalizedBar(
                symbol="SAP.DE",
                timeframe="1day",
                timestamp=datetime(2026, 3, 26, 0, 0, tzinfo=timezone.utc),
                open=Decimal("145.10"),
                high=Decimal("147.25"),
                low=Decimal("143.95"),
                close=Decimal("146.85"),
                volume=3567464,
                vwap=None,
                trades_count=None,
            ),
            NormalizedBar(
                symbol="SAP.DE",
                timeframe="1day",
                timestamp=datetime(2026, 3, 27, 0, 0, tzinfo=timezone.utc),
                open=Decimal("146.90"),
                high=Decimal("147.40"),
                low=Decimal("142.10"),
                close=Decimal("142.56"),
                volume=3567464,
                vwap=None,
                trades_count=None,
            ),
        ]

    monkeypatch.setattr("app.services.market_data_service.fetch_eodhd_eod_bars", fake_eodhd_bars)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "SAP.DE", "timeframe": "1day", "limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[-1]["symbol"] == "SAP.DE"
    assert payload[-1]["close"] == 142.56


def test_market_data_query_returns_empty_when_provider_is_temporarily_unavailable(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.ibkr_host = "127.0.0.1"

    def raise_rate_limit(*args, **kwargs):
        raise RuntimeError("IBKR market data temporarily unavailable.")

    monkeypatch.setattr("app.services.market_data_service.fetch_ibkr_historical_bars", raise_rate_limit)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "MSFT", "timeframe": "1min", "limit": 10},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_market_status_endpoint_uses_finnhub(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.finnhub_api_key = "test-token"

    def fake_market_status(*args, **kwargs) -> tuple[FinnhubMarketStatus, str]:
        return (
            FinnhubMarketStatus(
                exchange="US",
                holiday=None,
                is_open=False,
                session="pre-market",
                timezone_name="America/New_York",
                timestamp=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
            ),
            "finnhub",
        )

    monkeypatch.setattr("app.api.routes.market_data.get_market_status", fake_market_status)

    response = authenticated_client.get("/api/v1/market-data/market-status", params={"exchange": "US"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "finnhub"
    assert payload["exchange"] == "US"
    assert payload["session"] == "pre-market"


def test_market_data_symbols_endpoint_lists_tracked_markets(authenticated_client) -> None:
    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        session.add_all(
            [
                Symbol(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_type="equity", is_active=True),
                Symbol(ticker="IBM", name="IBM", exchange="NYSE", asset_type="equity", is_active=True),
                Symbol(ticker="ZZZZ", name="Inactive Name", exchange="NYSE", asset_type="equity", is_active=False),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = authenticated_client.get(
        "/api/v1/market-data/symbols",
        params={"exchange": "NYSE", "query": "ib", "limit": 20},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ticker"] == "IBM"
    assert payload[0]["exchange"] == "NYSE"
    assert payload[0]["asset_type"] == "equity"


def test_market_data_universe_endpoint_returns_live_provider_page(authenticated_client, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_universe(*args, **kwargs) -> MarketUniversePage:
        captured.update(kwargs)
        return MarketUniversePage(
            items=[
                MarketUniverseItem(
                    ticker="AAPL",
                    name="Apple Inc.",
                    exchange="XNAS",
                    asset_type="equity",
                    is_active=True,
                    market="stocks",
                    primary_exchange="XNAS",
                    security_type="CS",
                    currency="EUR",
                    round_lot_size=100,
                    minimum_order_size=1,
                    last_updated_utc=datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc),
                    last_price=248.80,
                    change=-4.09,
                    change_percent=-1.62,
                    quote_timestamp=datetime(2026, 3, 28, 14, 30, tzinfo=timezone.utc),
                    quote_source="eodhd",
                )
            ],
            next_cursor="cursor_live_123",
            source="eodhd-search",
            as_of=datetime(2026, 3, 28, 14, 30, tzinfo=timezone.utc),
        )

    monkeypatch.setattr("app.api.routes.market_data.list_market_universe", fake_universe)

    response = authenticated_client.get(
        "/api/v1/market-data/universe",
        params={
            "query": "apple",
            "limit": 10,
            "locale": "global",
            "currency": "EUR",
            "include_quotes": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured["locale"] == "global"
    assert captured["currency"] == "EUR"
    assert payload["source"] == "eodhd-search"
    assert payload["next_cursor"] == "cursor_live_123"
    assert payload["items"][0]["ticker"] == "AAPL"
    assert payload["items"][0]["round_lot_size"] == 100
    assert payload["items"][0]["last_price"] == 248.8
    assert payload["items"][0]["quote_source"] == "eodhd"


def test_market_data_universe_falls_back_to_local_symbols_when_provider_fails(authenticated_client, monkeypatch) -> None:
    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        session.add_all(
            [
                Symbol(ticker="AAPL", name="Apple Inc.", exchange="XNAS", asset_type="equity", is_active=True),
                Symbol(ticker="MSFT", name="Microsoft Corporation", exchange="XNAS", asset_type="equity", is_active=True),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = authenticated_client.get("/api/v1/market-data/universe", params={"limit": 24, "security_type": "CS"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "local-watchlist"
    assert {item["ticker"] for item in payload["items"]} >= {"AAPL", "MSFT"}


def test_market_data_euro_universe_request_filters_out_us_watchlist_symbols(authenticated_client) -> None:
    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        session.add_all(
            [
                Symbol(ticker="AAPL", name="Apple Inc.", exchange="XNAS", asset_type="equity", is_active=True),
                Symbol(ticker="MSFT", name="Microsoft Corporation", exchange="XNAS", asset_type="equity", is_active=True),
            ]
        )
        session.commit()
    finally:
        session.close()

    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        page = list_market_universe(
            session,
            authenticated_client.app.state.settings,
            locale="global",
            currency="EUR",
            limit=24,
            security_type="CS",
        )
    finally:
        session.close()

    assert page.source == "eodhd-watchlist-fallback"
    assert {item.ticker for item in page.items} >= {"SAP.DE", "MC.PA", "AIR.PA"}
    assert "AAPL" not in {item.ticker for item in page.items}


def test_market_data_refresh_updates_existing_bars(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.ibkr_host = "127.0.0.1"
    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        symbol = ensure_symbol(session, "AAPL")
        timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=1)
        session.add(
            MarketDataBar(
                symbol_id=symbol.id,
                timeframe="1min",
                timestamp=timestamp,
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.50"),
                close=Decimal("100.50"),
                volume=1000,
                vwap=Decimal("100.25"),
                trades_count=100,
            )
        )
        session.commit()
    finally:
        session.close()

    def fake_ibkr_bars(*args, **kwargs) -> list[NormalizedBar]:
        return [
            NormalizedBar(
                symbol="AAPL",
                timeframe="1min",
                timestamp=timestamp,
                open=Decimal("200.00"),
                high=Decimal("201.00"),
                low=Decimal("199.50"),
                close=Decimal("200.50"),
                volume=5000,
                vwap=None,
                trades_count=None,
            )
        ]

    monkeypatch.setattr("app.services.market_data_service.fetch_ibkr_historical_bars", fake_ibkr_bars)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "AAPL", "timeframe": "1min", "limit": 10, "refresh": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[-1]["close"] == 200.5
    assert payload[-1]["volume"] == 5000


def test_market_data_refresh_uses_cached_rows_when_provider_fails(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.ibkr_host = "127.0.0.1"
    session = authenticated_client.app.state.session_manager.session_factory()
    try:
        symbol = ensure_symbol(session, "MSFT")
        timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=1)
        session.add(
            MarketDataBar(
                symbol_id=symbol.id,
                timeframe="1min",
                timestamp=timestamp,
                open=Decimal("310.00"),
                high=Decimal("311.00"),
                low=Decimal("309.50"),
                close=Decimal("310.50"),
                volume=2000,
                vwap=Decimal("310.25"),
                trades_count=140,
            )
        )
        session.commit()
    finally:
        session.close()

    def raise_rate_limit(*args, **kwargs):
        raise RuntimeError("IBKR market data temporarily unavailable.")

    monkeypatch.setattr("app.services.market_data_service.fetch_ibkr_historical_bars", raise_rate_limit)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "MSFT", "timeframe": "1min", "limit": 10, "refresh": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[-1]["symbol"] == "MSFT"
    assert payload[-1]["close"] == 310.5


def test_preview_stream_returns_bars_outside_market_hours(monkeypatch) -> None:
    import app.services.polygon.stream as stream_module

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 3, 28, 1, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(stream_module, "datetime", FixedDateTime)

    bars = preview_stream(["MSFT"], timeframe="1min", points=72)["MSFT"]

    assert len(bars) == 72
    assert all(bar.symbol == "MSFT" for bar in bars)
