from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.symbol import Symbol
from app.services import broker_service
from app.services.backtest_service import backtest_detail, list_backtests, run_backtest
from app.services.feature_service import materialize_features
from app.services.market_data_service import backfill_market_data
from app.services.model_service import list_model_runs, train_baseline_models
from app.services.signal_service import generate_signals, list_signals
from app.services.system_log_service import list_logs


def seed_demo_environment(
    session: Session,
    settings: Settings,
    *,
    symbols: list[str],
    timeframe: str,
    days: int,
) -> dict[str, str | int]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(2, days))

    for symbol in symbols:
        backfill_market_data(
            session,
            settings,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            source="synthetic",
        )
        materialize_features(session, symbol=symbol, timeframe=timeframe, pipeline_version="v1")
        runs, _ = train_baseline_models(
            session,
            settings,
            symbol=symbol,
            timeframe=timeframe,
            pipeline_version="v1",
            label_horizon=1,
            return_threshold=0.0,
            buy_threshold=0.55,
            sell_threshold=0.45,
        )
        champion = next((run for run in runs if run.status == "champion"), runs[0])
        generate_signals(
            session,
            symbol=symbol,
            timeframe=timeframe,
            model_run_id=champion.id,
            buy_threshold=0.55,
            sell_threshold=0.45,
        )
        run_backtest(
            session,
            settings,
            symbol=symbol,
            timeframe=timeframe,
            model_run_id=champion.id,
            trade_size=10_000,
            transaction_cost_bps=1.0,
            slippage_bps=2.0,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            max_daily_loss=1_500,
            max_position_size=10_000,
            cooldown_minutes=15,
            max_exposure_per_symbol=10_000,
            buy_threshold=0.55,
            sell_threshold=0.45,
        )

    latest_signals = list_signals(session, limit=5)
    for signal, symbol in latest_signals[: min(2, len(latest_signals))]:
        if signal.signal_type in {"BUY", "SELL"}:
            broker_service.place_paper_order(
                session,
                settings,
                symbol=symbol,
                side=signal.signal_type,
                quantity=10,
                order_type="market",
                limit_price=None,
            )

    return {"status": "seeded", "symbols": len(symbols), "timeframe": timeframe}


def dashboard_snapshot(session: Session, settings: Settings) -> dict[str, object]:
    backtests = list_backtests(session, limit=5)
    model_runs = list_model_runs(session)[:5]
    signals = list_signals(session, limit=8)
    positions = broker_service.list_positions(session, limit=8)
    logs = list_logs(session, limit=8)
    symbol_map = {row.id: row.ticker for row in session.scalars(select(Symbol))}

    if not backtests and settings.demo_seed_file.exists():
        payload = json.loads(settings.demo_seed_file.read_text(encoding="utf-8"))
        return {
            "generated_at": datetime.now(timezone.utc),
            "mode": settings.execution_mode.value,
            "summary_cards": [
                {"label": "Portfolio Value", "value": payload["summary"]["portfolioValue"]},
                {"label": "Daily PnL", "value": payload["summary"]["dailyPnL"]},
                {"label": "Open Positions", "value": payload["summary"]["openPositions"]},
                {"label": "Latest Signal", "value": payload["summary"]["latestSignal"]},
            ],
            "equity_curve": [],
            "pnl_curve": [],
            "win_loss_distribution": [],
            "latest_signals": [],
            "positions": [],
            "backtests": [],
            "models": [],
            "logs": [],
        }

    latest_equity_curve: list[dict[str, str | float]] = []
    win_rate = 0.0
    max_drawdown = 0.0
    if backtests:
        run, _, latest_equity_curve = backtest_detail(session, backtests[0].id)
        metrics = run.metrics or {}
        win_rate = float(metrics.get("win_rate", 0.0))
        max_drawdown = float(metrics.get("max_drawdown", 0.0))

    portfolio_value = latest_equity_curve[-1]["equity"] if latest_equity_curve else 100_000.0
    daily_pnl = (
        float(latest_equity_curve[-1]["equity"]) - float(latest_equity_curve[-2]["equity"])
        if len(latest_equity_curve) > 1
        else 0.0
    )
    latest_signal = signals[0][0].signal_type if signals else "HOLD"

    return {
        "generated_at": datetime.now(timezone.utc),
        "mode": settings.execution_mode.value,
        "summary_cards": [
            {"label": "Portfolio Value", "value": round(float(portfolio_value), 2), "delta": daily_pnl},
            {"label": "Daily PnL", "value": round(daily_pnl, 2)},
            {"label": "Win Rate", "value": round(win_rate * 100, 2)},
            {"label": "Max Drawdown", "value": round(max_drawdown * 100, 2)},
            {"label": "Open Positions", "value": len([item for item in positions if float(item.quantity or 0) != 0])},
            {"label": "Latest Signal", "value": latest_signal},
        ],
        "equity_curve": latest_equity_curve,
        "pnl_curve": [
            {"timestamp": point["timestamp"], "pnl": round(float(point["equity"]) - 100_000.0, 2)}
            for point in latest_equity_curve
        ],
        "win_loss_distribution": [
            {"label": "Wins", "value": round(win_rate * 100, 2)},
            {"label": "Losses", "value": round((1 - win_rate) * 100, 2)},
        ],
        "latest_signals": [
            {
                "symbol": symbol,
                "timestamp": signal.timestamp.isoformat(),
                "signal_type": signal.signal_type,
                "confidence": float(signal.confidence or 0),
                "reason": signal.reason,
            }
            for signal, symbol in signals
        ],
        "positions": [
            {
                "symbol": symbol_map.get(position.symbol_id, "UNKNOWN"),
                "quantity": float(position.quantity),
                "average_price": float(position.average_price or 0),
                "market_value": float(position.market_value or 0),
                "unrealized_pnl": float(position.unrealized_pnl or 0),
                "status": position.status,
            }
            for position in positions
        ],
        "backtests": [
            {
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "total_return": float((run.metrics or {}).get("total_return", 0.0)),
                "sharpe": float((run.metrics or {}).get("sharpe", 0.0)),
                "trade_count": int((run.metrics or {}).get("trade_count", 0)),
            }
            for run in backtests
        ],
        "models": [
            {
                "id": run.id,
                "name": run.name,
                "model_type": run.model_type,
                "status": run.status,
                "f1": float((run.metrics or {}).get("f1", 0.0)),
                "roc_auc": float((run.metrics or {}).get("roc_auc", 0.0)),
            }
            for run in model_runs
        ],
        "logs": [
            {"timestamp": log.logged_at.isoformat(), "level": log.level, "message": log.message}
            for log in logs
        ],
    }
