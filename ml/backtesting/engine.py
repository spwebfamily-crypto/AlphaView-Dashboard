from __future__ import annotations

import argparse

from ml.training.utils import ensure_backend_on_path

ensure_backend_on_path()

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionManager  # noqa: E402
from app.services.backtest_service import run_backtest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a research backtest.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1min")
    args = parser.parse_args()

    settings = get_settings()
    session_manager = SessionManager(settings.database_url)
    session = session_manager.session_factory()
    try:
        run = run_backtest(
            session,
            settings,
            symbol=args.symbol,
            timeframe=args.timeframe,
            model_run_id=None,
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
        print(f"Backtest {run.id} completed with status {run.status}")
    finally:
        session.close()
        session_manager.dispose()


if __name__ == "__main__":
    main()

