from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.finnhub.historical import FinnhubCandleBar
from app.services.finnhub.market import FinnhubMarketStatus


def test_market_data_backfill_and_query(client: TestClient) -> None:
    response = client.post(
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

    bars_response = client.get(
        "/api/v1/market-data/bars",
        params={"symbol": "AAPL", "timeframe": "1min", "limit": 25},
    )
    assert bars_response.status_code == 200
    payload = bars_response.json()
    assert len(payload) > 0
    assert payload[0]["symbol"] == "AAPL"


def test_market_data_backfill_supports_finnhub_source(client: TestClient, monkeypatch) -> None:
    client.app.state.settings.finnhub_api_key = "test-token"

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

    response = client.post(
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


def test_market_status_endpoint_uses_finnhub(client: TestClient, monkeypatch) -> None:
    client.app.state.settings.finnhub_api_key = "test-token"

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

    response = client.get("/api/v1/market-data/market-status", params={"exchange": "US"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "finnhub"
    assert payload["exchange"] == "US"
    assert payload["session"] == "pre-market"
