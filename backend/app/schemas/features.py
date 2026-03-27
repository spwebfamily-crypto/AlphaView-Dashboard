from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FeatureMaterializationRequest(BaseModel):
    symbol: str
    timeframe: str = "1min"
    pipeline_version: str = "v1"


class FeatureRowResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    pipeline_version: str
    features: dict[str, float | int | None]


class FeatureMaterializationResponse(BaseModel):
    symbol: str
    timeframe: str
    pipeline_version: str
    rows_materialized: int
