from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.backtests import BacktestRequest, BacktestRunResponse, BacktestTradeResponse, EquityPoint
from app.utils.serializers import to_float

router = APIRouter(prefix="/backtests")


def run_backtest(*args, **kwargs):
    from app.services.backtest_service import run_backtest as service

    return service(*args, **kwargs)


def list_backtests(*args, **kwargs):
    from app.services.backtest_service import list_backtests as service

    return service(*args, **kwargs)


def backtest_detail(*args, **kwargs):
    from app.services.backtest_service import backtest_detail as service

    return service(*args, **kwargs)


@router.post("/run", response_model=BacktestRunResponse)
def run(
    payload: BacktestRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> BacktestRunResponse:
    row = run_backtest(
        session,
        request.app.state.settings,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        model_run_id=payload.model_run_id,
        trade_size=payload.trade_size,
        transaction_cost_bps=payload.transaction_cost_bps,
        slippage_bps=payload.slippage_bps,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        max_daily_loss=payload.max_daily_loss,
        max_position_size=payload.max_position_size,
        cooldown_minutes=payload.cooldown_minutes,
        max_exposure_per_symbol=payload.max_exposure_per_symbol,
        buy_threshold=payload.buy_threshold,
        sell_threshold=payload.sell_threshold,
    )
    detail_row, trades, equity_curve = backtest_detail(session, row.id)
    return _serialize_backtest(detail_row, trades, equity_curve, payload.symbol.upper())


@router.get("", response_model=list[BacktestRunResponse])
def list_runs(session: Session = Depends(get_db_session)) -> list[BacktestRunResponse]:
    responses: list[BacktestRunResponse] = []
    for row in list_backtests(session):
        responses.append(
            BacktestRunResponse(
                id=row.id,
                name=row.name,
                status=row.status,
                metrics=row.metrics,
                config=row.config,
                started_at=row.started_at,
                finished_at=row.finished_at,
            )
        )
    return responses


@router.get("/{backtest_run_id}", response_model=BacktestRunResponse)
def detail(backtest_run_id: int, session: Session = Depends(get_db_session)) -> BacktestRunResponse:
    run, trades, equity_curve = backtest_detail(session, backtest_run_id)
    return _serialize_backtest(run, trades, equity_curve, run.symbol_scope or "UNKNOWN")


def _serialize_backtest(run, trades, equity_curve, symbol: str) -> BacktestRunResponse:
    return BacktestRunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        metrics=run.metrics,
        config=run.config,
        started_at=run.started_at,
        finished_at=run.finished_at,
        equity_curve=[
            EquityPoint(
                timestamp=point["timestamp"],
                equity=float(point["equity"]),
                drawdown=float(point["drawdown"]),
            )
            for point in equity_curve
        ],
        trades=[
            BacktestTradeResponse(
                id=trade.id,
                symbol=symbol,
                side=trade.side,
                entry_time=trade.entry_time,
                exit_time=trade.exit_time,
                entry_price=to_float(trade.entry_price) or 0.0,
                exit_price=to_float(trade.exit_price),
                quantity=to_float(trade.quantity) or 0.0,
                pnl=to_float(trade.pnl),
                pnl_pct=to_float(trade.pnl_pct),
            )
            for trade in trades
        ],
    )

