from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionManager
from app.services.feature_service import materialize_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize engineered features.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1min")
    parser.add_argument("--pipeline-version", default="v1")
    args = parser.parse_args()

    settings = get_settings()
    session_manager = SessionManager(settings.database_url)
    session_manager.create_schema()
    session = session_manager.session_factory()
    try:
        rows = materialize_features(
            session,
            symbol=args.symbol,
            timeframe=args.timeframe,
            pipeline_version=args.pipeline_version,
        )
        print(f"Materialized {rows} feature rows for {args.symbol.upper()} {args.timeframe}")
    finally:
        session.close()
        session_manager.dispose()


if __name__ == "__main__":
    main()

