from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.signals import SignalGenerationRequest, SignalResponse
from app.services.signal_service import generate_signals, list_signals

router = APIRouter(prefix="/signals")


@router.post("/generate", response_model=list[SignalResponse])
def generate(
    payload: SignalGenerationRequest,
    session: Session = Depends(get_db_session),
) -> list[SignalResponse]:
    rows = generate_signals(
        session,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        model_run_id=payload.model_run_id,
        buy_threshold=payload.buy_threshold,
        sell_threshold=payload.sell_threshold,
    )
    return [
        SignalResponse(
            id=row.id,
            symbol=payload.symbol.upper(),
            timestamp=row.timestamp,
            signal_type=row.signal_type,
            confidence=float(row.confidence or 0),
            reason=row.reason,
            status=row.status,
        )
        for row in rows
    ]


@router.get("", response_model=list[SignalResponse])
def list_signal_rows(
    symbol: str | None = None,
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_db_session),
) -> list[SignalResponse]:
    rows = list_signals(session, symbol=symbol, limit=limit)
    return [
        SignalResponse(
            id=row.id,
            symbol=ticker,
            timestamp=row.timestamp,
            signal_type=row.signal_type,
            confidence=float(row.confidence or 0),
            reason=row.reason,
            status=row.status,
        )
        for row, ticker in rows
    ]
