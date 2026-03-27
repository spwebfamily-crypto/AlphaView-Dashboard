from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.demo import DashboardSnapshot, DemoSeedRequest, SummaryCard
from app.services.demo_service import dashboard_snapshot, seed_demo_environment

router = APIRouter(prefix="/demo")


@router.post("/seed")
def seed(
    payload: DemoSeedRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, str | int]:
    return seed_demo_environment(
        session,
        request.app.state.settings,
        symbols=[symbol.upper() for symbol in payload.symbols],
        timeframe=payload.timeframe,
        days=payload.days,
    )


@router.get("/snapshot", response_model=DashboardSnapshot)
def snapshot(request: Request, session: Session = Depends(get_db_session)) -> DashboardSnapshot:
    payload = dashboard_snapshot(session, request.app.state.settings)
    return DashboardSnapshot(
        generated_at=payload["generated_at"],
        mode=payload["mode"],
        summary_cards=[SummaryCard(**item) for item in payload["summary_cards"]],
        equity_curve=payload["equity_curve"],
        pnl_curve=payload["pnl_curve"],
        win_loss_distribution=payload["win_loss_distribution"],
        latest_signals=payload["latest_signals"],
        positions=payload["positions"],
        backtests=payload["backtests"],
        models=payload["models"],
        logs=payload["logs"],
    )

