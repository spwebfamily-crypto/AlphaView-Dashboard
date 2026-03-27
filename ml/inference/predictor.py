from __future__ import annotations

import argparse

from ml.training.utils import ensure_backend_on_path

ensure_backend_on_path()

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionManager  # noqa: E402
from app.services.model_service import latest_inference  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run latest model inference.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1min")
    parser.add_argument("--pipeline-version", default="v1")
    args = parser.parse_args()

    settings = get_settings()
    session_manager = SessionManager(settings.database_url)
    session = session_manager.session_factory()
    try:
        print(
            latest_inference(
                session,
                symbol=args.symbol,
                timeframe=args.timeframe,
                pipeline_version=args.pipeline_version,
            )
        )
    finally:
        session.close()
        session_manager.dispose()


if __name__ == "__main__":
    main()

