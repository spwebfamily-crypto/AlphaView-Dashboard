from __future__ import annotations

import argparse
import time

from app.core.config import get_settings
from app.workers.retrain_worker import run_retraining


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple periodic retraining scheduler.")
    parser.add_argument("--interval-minutes", type=int, default=60)
    args = parser.parse_args()

    settings = get_settings()
    print(
        f"Starting AlphaView scheduler in {settings.execution_mode.value} mode. "
        f"Retrain interval: {args.interval_minutes} minutes."
    )
    while True:
        run_retraining(settings.default_symbols, settings.default_timeframe, "v1")
        time.sleep(max(1, args.interval_minutes) * 60)


if __name__ == "__main__":
    main()
