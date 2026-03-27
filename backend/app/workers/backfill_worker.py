from __future__ import annotations

import argparse
from app.core.config import get_settings
from app.db.session import SessionManager
from app.services.market_data_service import backfill_market_data
from app.utils.time import parse_iso_datetime


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical market data.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1min")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--source", default="auto")
    args = parser.parse_args()

    settings = get_settings()
    session_manager = SessionManager(settings.database_url)
    session_manager.create_schema()
    session = session_manager.session_factory()
    try:
        inserted, source = backfill_market_data(
            session,
            settings,
            symbol=args.symbol,
            timeframe=args.timeframe,
            start=parse_iso_datetime(args.start),
            end=parse_iso_datetime(args.end),
            source=args.source,
        )
        print(f"Backfilled {inserted} rows from {source} for {args.symbol.upper()} {args.timeframe}")
    finally:
        session.close()
        session_manager.dispose()


if __name__ == "__main__":
    main()
