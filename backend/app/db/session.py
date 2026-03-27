from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


class SessionManager:
    def __init__(self, database_url: str) -> None:
        engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                engine_kwargs["poolclass"] = StaticPool

        self.engine = create_engine(database_url, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(bind=self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    def get_session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def healthcheck(self) -> str:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"

