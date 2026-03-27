from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.services.polygon.historical import PolygonAggregateBar
from app.services.finnhub.historical import FinnhubCandleBar
from app.services.finnhub.market import FinnhubMarketStatus


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


def test_market_data_query_auto_fetches_polygon_when_store_is_empty(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.polygon_api_key = "test-token"

    def fake_polygon_bars(*args, **kwargs) -> list[PolygonAggregateBar]:
        return [
            PolygonAggregateBar(
                timestamp=datetime(2026, 3, 26, 14, 30, tzinfo=timezone.utc),
                open=Decimal("170.10"),
                high=Decimal("171.25"),
                low=Decimal("169.95"),
                close=Decimal("170.85"),
                volume=4500000,
                vwap=Decimal("170.55"),
                trades_count=12034,
            ),
            PolygonAggregateBar(
                timestamp=datetime(2026, 3, 26, 14, 31, tzinfo=timezone.utc),
                open=Decimal("170.85"),
                high=Decimal("171.40"),
                low=Decimal("170.60"),
                close=Decimal("171.20"),
                volume=4250000,
                vwap=Decimal("171.01"),
                trades_count=11321,
            ),
        ]

    monkeypatch.setattr("app.services.market_data_service.normalize_polygon_aggregates", fake_polygon_bars)

    response = authenticated_client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "AAPL", "timeframe": "1min", "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["symbol"] == "AAPL"
    assert payload[0]["close"] == 170.85


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
