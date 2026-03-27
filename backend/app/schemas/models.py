from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrainingRequest(BaseModel):
    symbol: str
    timeframe: str = "1min"
    pipeline_version: str = "v1"
    label_horizon: int = 1
    return_threshold: float = 0.0
    buy_threshold: float = 0.55
    sell_threshold: float = 0.45


class ModelRunResponse(BaseModel):
    id: int
    name: str
    model_type: str
    status: str
    dataset_version: str | None = None
    feature_version: str | None = None
    metrics: dict[str, float | int | str | None] | None = None
    artifact_path: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TrainResponse(BaseModel):
    symbol: str
    timeframe: str
    runs: list[ModelRunResponse]
    predictions_generated: int


class InferenceResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    probability_up: float
    probability_down: float
    action: str
    confidence: float
