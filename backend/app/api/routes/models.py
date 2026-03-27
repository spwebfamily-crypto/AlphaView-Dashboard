from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.models import InferenceResponse, ModelRunResponse, TrainResponse, TrainingRequest

router = APIRouter(prefix="/models")


def train_baseline_models(*args, **kwargs):
    from app.services.model_service import train_baseline_models as service

    return service(*args, **kwargs)


def list_model_runs(*args, **kwargs):
    from app.services.model_service import list_model_runs as service

    return service(*args, **kwargs)


def serialize_model_run(*args, **kwargs):
    from app.services.model_service import serialize_model_run as service

    return service(*args, **kwargs)


def latest_inference(*args, **kwargs):
    from app.services.model_service import latest_inference as service

    return service(*args, **kwargs)


@router.post("/train", response_model=TrainResponse)
def train_models(
    payload: TrainingRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> TrainResponse:
    runs, prediction_count = train_baseline_models(
        session,
        request.app.state.settings,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        pipeline_version=payload.pipeline_version,
        label_horizon=payload.label_horizon,
        return_threshold=payload.return_threshold,
        buy_threshold=payload.buy_threshold,
        sell_threshold=payload.sell_threshold,
    )
    return TrainResponse(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        runs=[ModelRunResponse(**serialize_model_run(run)) for run in runs],
        predictions_generated=prediction_count,
    )


@router.get("/runs", response_model=list[ModelRunResponse])
def model_runs(
    symbol: str | None = None,
    timeframe: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[ModelRunResponse]:
    return [ModelRunResponse(**serialize_model_run(run)) for run in list_model_runs(session, symbol, timeframe)]


@router.get("/latest", response_model=InferenceResponse)
def latest_model_inference(
    symbol: str,
    timeframe: str = "1min",
    pipeline_version: str = "v1",
    buy_threshold: float = 0.55,
    sell_threshold: float = 0.45,
    session: Session = Depends(get_db_session),
) -> InferenceResponse:
    payload = latest_inference(
        session,
        symbol=symbol,
        timeframe=timeframe,
        pipeline_version=pipeline_version,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )
    return InferenceResponse(**payload)

