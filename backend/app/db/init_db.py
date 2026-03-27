from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionManager
from app.models import *  # noqa: F401,F403


def main() -> None:
    settings = get_settings()
    configure_logging(settings.app_env)
    session_manager = SessionManager(settings.database_url)
    session_manager.create_schema()
    session_manager.dispose()


if __name__ == "__main__":
    main()

