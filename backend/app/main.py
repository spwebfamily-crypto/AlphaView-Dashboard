from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import SessionManager
from app.models import *  # noqa: F401,F403


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.app_env)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        session_manager = SessionManager(runtime_settings.database_url)
        session_manager.create_schema()

        app.state.settings = runtime_settings
        app.state.session_manager = session_manager
        try:
            yield
        finally:
            session_manager.dispose()

    app = FastAPI(
        title=runtime_settings.project_name,
        version=runtime_settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()

