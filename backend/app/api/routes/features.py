from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.features import (
    FeatureMaterializationRequest,
    FeatureMaterializationResponse,
    FeatureRowResponse,
)
from app.services.feature_service import get_feature_rows, materialize_features

router = APIRouter(prefix="/features")


@router.post("/materialize", response_model=FeatureMaterializationResponse)
def materialize(
    payload: FeatureMaterializationRequest,
    session: Session = Depends(get_db_session),
) -> FeatureMaterializationResponse:
    rows = materialize_features(
        session,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        pipeline_version=payload.pipeline_version,
    )
    return FeatureMaterializationResponse(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        pipeline_version=payload.pipeline_version,
        rows_materialized=rows,
    )


@router.get("", response_model=list[FeatureRowResponse])
def list_feature_rows(
    symbol: str,
    timeframe: str = "1min",
    pipeline_version: str = "v1",
    limit: int = Query(default=200, le=5000),
    session: Session = Depends(get_db_session),
) -> list[FeatureRowResponse]:
    rows = get_feature_rows(
        session,
        symbol=symbol,
        timeframe=timeframe,
        pipeline_version=pipeline_version,
        limit=limit,
    )
    return [
        FeatureRowResponse(
            symbol=ticker,
            timeframe=row.timeframe,
            timestamp=row.timestamp,
            pipeline_version=row.pipeline_version,
            features=row.features,
        )
        for row, ticker in rows
    ]

