from fastapi import APIRouter

from app.api.routes.backtests import router as backtests_router
from app.api.routes.broker import router as broker_router
from app.api.routes.demo import router as demo_router
from app.api.routes.features import router as features_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.models import router as models_router
from app.api.routes.settings import router as settings_router
from app.api.routes.signals import router as signals_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(market_data_router, tags=["market-data"])
api_router.include_router(features_router, tags=["features"])
api_router.include_router(models_router, tags=["models"])
api_router.include_router(signals_router, tags=["signals"])
api_router.include_router(backtests_router, tags=["backtests"])
api_router.include_router(broker_router, tags=["broker"])
api_router.include_router(demo_router, tags=["demo"])
api_router.include_router(logs_router, tags=["logs"])
api_router.include_router(settings_router, tags=["settings"])
