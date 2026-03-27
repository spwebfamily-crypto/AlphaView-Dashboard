from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck(request: Request) -> HealthResponse:
    session_manager = request.app.state.session_manager
    settings = request.app.state.settings

    return HealthResponse(
        status="ok",
        service=settings.project_name,
        version=settings.app_version,
        environment=settings.app_env,
        execution_mode=settings.execution_mode.value,
        live_trading_enabled=settings.enable_live_trading,
        database=session_manager.healthcheck(),
    )

