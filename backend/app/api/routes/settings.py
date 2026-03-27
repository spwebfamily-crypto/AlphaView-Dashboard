from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.settings import RuntimeSettingsResponse

router = APIRouter(prefix="/settings")


def configured_market_data_sources(*args, **kwargs):
    from app.services.market_data_service import configured_market_data_sources as service

    return service(*args, **kwargs)


@router.get("/runtime", response_model=RuntimeSettingsResponse)
def runtime_settings(request: Request) -> RuntimeSettingsResponse:
    settings = request.app.state.settings
    return RuntimeSettingsResponse(
        project_name=settings.project_name,
        environment=settings.app_env,
        execution_mode=settings.execution_mode.value,
        live_trading_enabled=settings.enable_live_trading,
        broker_adapter=settings.broker_adapter,
        default_symbols=settings.default_symbols,
        default_timeframe=settings.default_timeframe,
        available_market_data_sources=configured_market_data_sources(settings),
        market_status_provider="finnhub" if settings.finnhub_api_key else None,
    )
