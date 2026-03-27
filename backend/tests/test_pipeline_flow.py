from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feature_row import FeatureRow
from app.models.market_bar import MarketDataBar
from app.services.feature_service import materialize_features
from app.services.market_data_service import generate_synthetic_bars, upsert_bars


def test_feature_materialization_has_no_future_leakage(db_session: Session) -> None:
    bars = generate_synthetic_bars(
        symbol="AAPL",
        timeframe="1min",
        start=datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc),
        end=datetime(2026, 1, 7, 20, 0, tzinfo=timezone.utc),
    )
    upsert_bars(db_session, symbol="AAPL", timeframe="1min", bars=bars)
    materialize_features(db_session, symbol="AAPL", timeframe="1min", pipeline_version="v1")

    initial_rows = list(
        db_session.scalars(select(FeatureRow).order_by(FeatureRow.timestamp.asc()))
    )
    anchor_row = initial_rows[45]
    anchor_timestamp = anchor_row.timestamp
    anchor_features = dict(anchor_row.features)

    latest_bar = db_session.scalar(
        select(MarketDataBar).order_by(MarketDataBar.timestamp.desc()).limit(1)
    )
    assert latest_bar is not None
    latest_bar.close = 99999
    db_session.commit()

    materialize_features(db_session, symbol="AAPL", timeframe="1min", pipeline_version="v1")
    rematerialized_rows = list(
        db_session.scalars(select(FeatureRow).order_by(FeatureRow.timestamp.asc()))
    )
    same_timestamp_row = rematerialized_rows[45]

    assert same_timestamp_row.timestamp == anchor_timestamp
    assert same_timestamp_row.features == anchor_features


def test_training_signal_and_backtest_flow(authenticated_client) -> None:
    authenticated_client.post(
        "/api/v1/market-data/backfill",
        json={
            "symbol": "MSFT",
            "timeframe": "1min",
            "start": "2026-01-05T14:30:00Z",
            "end": "2026-01-10T20:00:00Z",
            "source": "synthetic",
        },
    )
    feature_response = authenticated_client.post(
        "/api/v1/features/materialize",
        json={"symbol": "MSFT", "timeframe": "1min", "pipeline_version": "v1"},
    )
    assert feature_response.status_code == 200
    assert feature_response.json()["rows_materialized"] > 0

    model_response = authenticated_client.post(
        "/api/v1/models/train",
        json={"symbol": "MSFT", "timeframe": "1min", "pipeline_version": "v1"},
    )
    assert model_response.status_code == 200
    model_payload = model_response.json()
    assert len(model_payload["runs"]) == 2

    signal_response = authenticated_client.post(
        "/api/v1/signals/generate",
        json={"symbol": "MSFT", "timeframe": "1min"},
    )
    assert signal_response.status_code == 200
    assert len(signal_response.json()) > 0

    backtest_response = authenticated_client.post(
        "/api/v1/backtests/run",
        json={"symbol": "MSFT", "timeframe": "1min"},
    )
    assert backtest_response.status_code == 200
    backtest_payload = backtest_response.json()
    assert backtest_payload["metrics"]["trade_count"] > 0
    assert len(backtest_payload["trades"]) > 0


def test_paper_broker_order_flow(authenticated_client) -> None:
    order_response = authenticated_client.post(
        "/api/v1/broker/orders",
        json={"symbol": "NVDA", "side": "BUY", "quantity": 10, "order_type": "market"},
    )
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "filled"

    positions_response = authenticated_client.get("/api/v1/broker/positions")
    assert positions_response.status_code == 200
    assert len(positions_response.json()) >= 1

    executions_response = authenticated_client.get("/api/v1/broker/executions")
    assert executions_response.status_code == 200
    assert len(executions_response.json()) >= 1
