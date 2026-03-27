from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.backtest_run import BacktestRun
from app.models.backtest_trade import BacktestTrade
from app.models.market_bar import MarketDataBar
from app.models.prediction import Prediction
from app.services.market_data_service import ensure_symbol
from app.services.model_service import latest_model_run
from app.services.risk_service import evaluate_trade_risk
from app.services.signal_service import classify_action
from app.services.system_log_service import log_event


def run_backtest(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    model_run_id: int | None,
    trade_size: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    max_daily_loss: float,
    max_position_size: float,
    cooldown_minutes: int,
    max_exposure_per_symbol: float,
    buy_threshold: float,
    sell_threshold: float,
) -> BacktestRun:
    symbol_row = ensure_symbol(session, symbol)
    selected_model_run = model_run_id or (latest_model_run(session, symbol=symbol, timeframe=timeframe) or BacktestRun()).id
    if selected_model_run is None:
        raise RuntimeError("No model run is available for backtesting.")

    predictions = list(
        session.scalars(
            select(Prediction)
            .where(
                and_(
                    Prediction.symbol_id == symbol_row.id,
                    Prediction.timeframe == timeframe,
                    Prediction.model_run_id == selected_model_run,
                )
            )
            .order_by(Prediction.timestamp.asc())
        )
    )
    bars = list(
        session.scalars(
            select(MarketDataBar)
            .where(
                and_(
                    MarketDataBar.symbol_id == symbol_row.id,
                    MarketDataBar.timeframe == timeframe,
                )
            )
            .order_by(MarketDataBar.timestamp.asc())
        )
    )
    if not predictions or len(bars) < 2:
        raise RuntimeError("Backtest requires predictions and market bars.")

    backtest_run = BacktestRun(
        name=f"{symbol.upper()}-{timeframe}-baseline-backtest",
        status="running",
        symbol_scope=symbol.upper(),
        config={
            "timeframe": timeframe,
            "model_run_id": selected_model_run,
            "trade_size": trade_size,
            "transaction_cost_bps": transaction_cost_bps,
            "slippage_bps": slippage_bps,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
        },
        started_at=datetime.now(timezone.utc),
    )
    session.add(backtest_run)
    session.commit()
    session.refresh(backtest_run)

    timestamp_to_index = {bar.timestamp: index for index, bar in enumerate(bars)}
    equity = 100_000.0
    peak = equity
    daily_pnl: dict[str, float] = defaultdict(float)
    last_trade_at: datetime | None = None
    equity_curve: list[dict[str, str | float]] = []
    trade_returns: list[float] = []

    for prediction in predictions:
        index = timestamp_to_index.get(prediction.timestamp)
        if index is None or index + 1 >= len(bars):
            continue
        next_bar = bars[index + 1]
        action = classify_action(float(prediction.probability_up or 0.5), buy_threshold, sell_threshold)
        trade_day = next_bar.timestamp.date().isoformat()
        risk = evaluate_trade_risk(
            action=action,
            trade_size=trade_size,
            max_position_size=max_position_size,
            max_exposure_per_symbol=max_exposure_per_symbol,
            max_daily_loss=max_daily_loss,
            daily_pnl=daily_pnl[trade_day],
            last_trade_at=last_trade_at,
            current_timestamp=next_bar.timestamp,
            cooldown_minutes=cooldown_minutes,
        )
        if not risk.allowed:
            continue

        direction = 1 if action == "BUY" else -1
        entry_price = float(next_bar.open) * (1 + direction * slippage_bps / 10_000)
        exit_price = float(next_bar.close) * (1 - direction * slippage_bps / 10_000)
        gross_return = direction * ((exit_price - entry_price) / max(entry_price, 0.01))
        clipped_return = float(np.clip(gross_return, -stop_loss_pct, take_profit_pct))
        net_return = clipped_return - (2 * transaction_cost_bps / 10_000)
        quantity = trade_size / max(entry_price, 0.01)
        pnl = trade_size * net_return

        session.add(
            BacktestTrade(
                backtest_run_id=backtest_run.id,
                symbol_id=symbol_row.id,
                side=action,
                entry_time=next_bar.timestamp,
                exit_time=next_bar.timestamp,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                pnl=pnl,
                pnl_pct=net_return,
            )
        )
        equity += pnl
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1 if peak else 0.0
        equity_curve.append(
            {
                "timestamp": next_bar.timestamp.isoformat(),
                "equity": round(equity, 2),
                "drawdown": round(drawdown, 6),
            }
        )
        trade_returns.append(net_return)
        daily_pnl[trade_day] += pnl
        last_trade_at = next_bar.timestamp

    session.commit()
    trades = list(
        session.scalars(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_run_id == backtest_run.id)
            .order_by(BacktestTrade.entry_time.asc())
        )
    )
    metrics = compute_backtest_metrics(trade_returns, trades, starting_equity=100_000.0, ending_equity=equity)

    settings.backtest_report_path.mkdir(parents=True, exist_ok=True)
    report_path = settings.backtest_report_path / f"backtest_{backtest_run.id}.json"
    report_path.write_text(
        json.dumps({"equity_curve": equity_curve, "metrics": metrics}, indent=2),
        encoding="utf-8",
    )

    backtest_run.status = "completed"
    backtest_run.metrics = metrics
    backtest_run.config = {**(backtest_run.config or {}), "report_path": str(report_path)}
    backtest_run.finished_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(backtest_run)

    log_event(
        session,
        level="INFO",
        source="backtesting",
        event_type="backtest_completed",
        message=f"Completed backtest {backtest_run.id} for {symbol.upper()} {timeframe}",
        context={"backtest_run_id": backtest_run.id, "trades": len(trades)},
    )
    return backtest_run


def compute_backtest_metrics(
    trade_returns: list[float],
    trades: list[BacktestTrade],
    *,
    starting_equity: float,
    ending_equity: float,
) -> dict[str, float]:
    returns_array = np.array(trade_returns, dtype=float)
    wins = returns_array[returns_array > 0]
    losses = returns_array[returns_array < 0]
    equity_series = np.array([starting_equity, ending_equity], dtype=float)
    max_drawdown = float((equity_series / np.maximum.accumulate(equity_series) - 1).min())
    sharpe = float((returns_array.mean() / returns_array.std()) * np.sqrt(252)) if returns_array.size > 1 and returns_array.std() > 0 else 0.0
    return {
        "total_return": float((ending_equity / starting_equity) - 1),
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": float((returns_array > 0).mean()) if returns_array.size else 0.0,
        "expectancy": float(returns_array.mean()) if returns_array.size else 0.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if losses.size else float(wins.sum()),
        "average_trade_return": float(returns_array.mean()) if returns_array.size else 0.0,
        "trade_count": float(len(trades)),
    }


def list_backtests(session: Session, limit: int = 20) -> list[BacktestRun]:
    return list(session.scalars(select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(limit)))


def backtest_detail(
    session: Session, backtest_run_id: int
) -> tuple[BacktestRun, list[BacktestTrade], list[dict[str, str | float]]]:
    run = session.scalar(select(BacktestRun).where(BacktestRun.id == backtest_run_id))
    if run is None:
        raise RuntimeError("Backtest run not found.")

    trades = list(
        session.scalars(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_run_id == backtest_run_id)
            .order_by(BacktestTrade.entry_time.asc())
        )
    )
    equity_curve: list[dict[str, str | float]] = []
    report_value = (run.config or {}).get("report_path")
    if report_value:
        report_path = Path(report_value)
    else:
        report_path = None
    if report_path is not None and report_path.exists():
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        equity_curve = payload.get("equity_curve", [])
    return run, trades, equity_curve
