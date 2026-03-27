from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionManager
from app.services.model_service import train_baseline_models


def run_retraining(symbols: list[str], timeframe: str, pipeline_version: str = "v1") -> None:
    settings = get_settings()
    session_manager = SessionManager(settings.database_url)
    session_manager.create_schema()
    session = session_manager.session_factory()
    try:
        for symbol in symbols:
            runs, predictions = train_baseline_models(
                session,
                settings,
                symbol=symbol,
                timeframe=timeframe,
                pipeline_version=pipeline_version,
                label_horizon=1,
                return_threshold=0.0,
                buy_threshold=0.55,
                sell_threshold=0.45,
            )
            print(
                f"Retrained {len(runs)} models for {symbol} {timeframe}; "
                f"stored {predictions} predictions."
            )
    finally:
        session.close()
        session_manager.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain supervised baseline models.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--pipeline-version", default="v1")
    args = parser.parse_args()

    settings = get_settings()
    timeframe = args.timeframe or settings.default_timeframe
    symbols = [args.symbol.upper()] if args.symbol else settings.default_symbols
    run_retraining(symbols, timeframe, args.pipeline_version)


if __name__ == "__main__":
    main()
