from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.models.signal import Signal
from app.models.symbol import Symbol
from app.services.market_data_service import ensure_symbol
from app.services.system_log_service import log_event


def classify_action(probability_up: float, buy_threshold: float, sell_threshold: float) -> str:
    if probability_up >= buy_threshold:
        return "BUY"
    if probability_up <= sell_threshold:
        return "SELL"
    return "HOLD"


def generate_signals(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    model_run_id: int | None,
    buy_threshold: float,
    sell_threshold: float,
) -> list[Signal]:
    symbol_row = ensure_symbol(session, symbol)
    query = select(Prediction).where(
        Prediction.symbol_id == symbol_row.id,
        Prediction.timeframe == timeframe,
    )
    if model_run_id is not None:
        query = query.where(Prediction.model_run_id == model_run_id)
    predictions = list(session.scalars(query.order_by(Prediction.timestamp.asc())))
    created: list[Signal] = []

    for prediction in predictions:
        probability_up = float(prediction.probability_up or 0.5)
        action = classify_action(probability_up, buy_threshold, sell_threshold)
        existing = session.scalar(select(Signal).where(Signal.prediction_id == prediction.id))
        if existing is not None:
            existing.signal_type = action
            existing.confidence = max(probability_up, 1 - probability_up)
            existing.reason = f"probability_up={probability_up:.4f}"
            created.append(existing)
            continue

        signal = Signal(
            prediction_id=prediction.id,
            symbol_id=symbol_row.id,
            timestamp=prediction.timestamp,
            signal_type=action,
            confidence=max(probability_up, 1 - probability_up),
            reason=f"probability_up={probability_up:.4f}",
            status="generated",
        )
        session.add(signal)
        created.append(signal)

    session.commit()
    log_event(
        session,
        level="INFO",
        source="signals",
        event_type="signals_generated",
        message=f"Generated {len(created)} signals for {symbol_row.ticker} {timeframe}",
        context={"symbol": symbol_row.ticker, "timeframe": timeframe, "count": len(created)},
    )
    return created


def list_signals(session: Session, *, symbol: str | None = None, limit: int = 100) -> list[tuple[Signal, str]]:
    symbols = {row.id: row.ticker for row in session.scalars(select(Symbol))}
    query = select(Signal).order_by(desc(Signal.timestamp)).limit(limit)
    if symbol:
        symbol_row = ensure_symbol(session, symbol)
        query = select(Signal).where(Signal.symbol_id == symbol_row.id).order_by(desc(Signal.timestamp)).limit(limit)
        return [(row, symbol_row.ticker) for row in session.scalars(query)]

    rows = list(session.scalars(query))
    return [(row, symbols.get(row.symbol_id, "UNKNOWN")) for row in rows]
