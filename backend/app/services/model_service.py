from __future__ import annotations

import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.model_run import ModelRun
from app.models.prediction import Prediction
from app.services.feature_service import FEATURE_COLUMNS, feature_dataset_frame
from app.services.market_data_service import ensure_symbol
from app.services.signal_service import classify_action
from app.services.system_log_service import log_event


def train_baseline_models(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    timeframe: str,
    pipeline_version: str,
    label_horizon: int,
    return_threshold: float,
    buy_threshold: float,
    sell_threshold: float,
) -> tuple[list[ModelRun], int]:
    dataset = feature_dataset_frame(
        session,
        symbol=symbol,
        timeframe=timeframe,
        pipeline_version=pipeline_version,
    )
    if dataset.empty or len(dataset) < 80:
        raise RuntimeError("Not enough feature rows to train a baseline model.")

    dataset["future_close"] = dataset["close"].shift(-label_horizon)
    dataset["future_return"] = (dataset["future_close"] / dataset["close"]) - 1
    dataset["label"] = (dataset["future_return"] > return_threshold).astype(int)
    dataset = dataset.iloc[:-label_horizon].reset_index(drop=True)

    feature_columns = [column for column in FEATURE_COLUMNS if column in dataset.columns]
    feature_matrix = dataset[feature_columns].fillna(0.0)
    labels = dataset["label"].astype(int)

    n_rows = len(dataset)
    train_end = max(20, int(n_rows * 0.6))
    val_end = max(train_end + 10, int(n_rows * 0.8))

    x_train = feature_matrix.iloc[:train_end]
    y_train = labels.iloc[:train_end]
    x_test = feature_matrix.iloc[val_end:]
    y_test = labels.iloc[val_end:]
    returns_test = dataset["future_return"].iloc[val_end:].to_numpy()
    timestamps_test = dataset["timestamp"].iloc[val_end:].tolist()

    model_specs = [
        (
            "logistic_regression",
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, random_state=42)),
        ),
        ("hist_gradient_boosting", HistGradientBoostingClassifier(random_state=42)),
    ]

    settings.model_registry_path.mkdir(parents=True, exist_ok=True)
    trained_runs: list[tuple[ModelRun, np.ndarray]] = []

    for model_name, estimator in model_specs:
        run = ModelRun(
            name=f"{symbol.upper()}-{timeframe}-{model_name}",
            model_type=model_name,
            dataset_version=f"{symbol.upper()}-{timeframe}-dataset",
            feature_version=pipeline_version,
            status="training",
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        estimator.fit(x_train, y_train)
        probabilities = estimator.predict_proba(x_test)[:, 1]
        metrics = compute_classification_metrics(y_test.to_numpy(), probabilities, returns_test)

        artifact_path = settings.model_registry_path / f"model_run_{run.id}_{model_name}.pkl"
        with artifact_path.open("wb") as artifact_file:
            pickle.dump(
                {
                    "model": estimator,
                    "feature_columns": feature_columns,
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                },
                artifact_file,
            )

        run.status = "completed"
        run.metrics = metrics
        run.artifact_path = str(artifact_path)
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
        trained_runs.append((run, probabilities))

    champion_run, champion_probabilities = max(
        trained_runs,
        key=lambda item: float((item[0].metrics or {}).get("f1", 0.0)),
    )
    for run, _ in trained_runs:
        run.status = "champion" if run.id == champion_run.id else "completed"
    session.commit()

    session.execute(delete(Prediction).where(Prediction.model_run_id == champion_run.id))
    symbol_row = ensure_symbol(session, symbol)
    for timestamp, label, probability_up in zip(
        timestamps_test, y_test.to_list(), champion_probabilities, strict=False
    ):
        session.add(
            Prediction(
                model_run_id=champion_run.id,
                symbol_id=symbol_row.id,
                timeframe=timeframe,
                timestamp=timestamp,
                label=str(int(label)),
                probability_up=float(probability_up),
                probability_down=float(1 - probability_up),
                raw_output={
                    "action": classify_action(probability_up, buy_threshold, sell_threshold),
                    "thresholds": {"buy": buy_threshold, "sell": sell_threshold},
                },
            )
        )
    session.commit()

    log_event(
        session,
        level="INFO",
        source="models",
        event_type="training_completed",
        message=f"Trained baseline models for {symbol.upper()} {timeframe}",
        context={
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "champion_model_run_id": champion_run.id,
            "predictions": len(champion_probabilities),
        },
    )
    return [run for run, _ in trained_runs], len(champion_probabilities)


def compute_classification_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    returns: np.ndarray,
) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(int)
    trade_mask = (probabilities >= 0.55) | (probabilities <= 0.45)
    trade_returns = returns[trade_mask]
    positive = trade_returns[trade_returns > 0]
    negative = trade_returns[trade_returns < 0]

    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)) if len(np.unique(labels)) > 1 else 0.5,
        "win_rate": float((trade_returns > 0).mean()) if trade_returns.size else 0.0,
        "expectancy": float(trade_returns.mean()) if trade_returns.size else 0.0,
        "profit_factor": float(positive.sum() / abs(negative.sum())) if negative.size else float(positive.sum()),
    }


def list_model_runs(session: Session, symbol: str | None = None, timeframe: str | None = None) -> list[ModelRun]:
    query = select(ModelRun).order_by(desc(ModelRun.created_at))
    if symbol and timeframe:
        query = query.where(ModelRun.dataset_version.like(f"{symbol.upper()}-{timeframe}%"))
    return list(session.scalars(query))


def latest_model_run(session: Session, *, symbol: str, timeframe: str) -> ModelRun | None:
    return session.scalar(
        select(ModelRun)
        .where(
            and_(
                ModelRun.dataset_version.like(f"{symbol.upper()}-{timeframe}%"),
                ModelRun.status.in_(["champion", "completed"]),
            )
        )
        .order_by((ModelRun.status == "champion").desc(), ModelRun.finished_at.desc())
        .limit(1)
    )


def latest_inference(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    pipeline_version: str = "v1",
    buy_threshold: float = 0.55,
    sell_threshold: float = 0.45,
) -> dict[str, float | str | datetime]:
    run = latest_model_run(session, symbol=symbol, timeframe=timeframe)
    if run is None or not run.artifact_path:
        raise RuntimeError("No trained model run is available for inference.")

    artifact_path = Path(run.artifact_path)
    with artifact_path.open("rb") as artifact_file:
        artifact = pickle.load(artifact_file)

    dataset = feature_dataset_frame(
        session,
        symbol=symbol,
        timeframe=timeframe,
        pipeline_version=pipeline_version,
    )
    if dataset.empty:
        raise RuntimeError("No feature rows are available for inference.")

    feature_columns = artifact["feature_columns"]
    latest_row = dataset.iloc[-1]
    probabilities = artifact["model"].predict_proba(dataset[feature_columns].fillna(0.0).iloc[[-1]])[0]
    probability_up = float(probabilities[1])
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "timestamp": latest_row["timestamp"],
        "probability_up": probability_up,
        "probability_down": float(probabilities[0]),
        "action": classify_action(probability_up, buy_threshold, sell_threshold),
        "confidence": float(max(probabilities)),
    }


def serialize_model_run(run: ModelRun) -> dict[str, str | int | float | dict[str, float] | None | datetime]:
    return {
        "id": run.id,
        "name": run.name,
        "model_type": run.model_type,
        "status": run.status,
        "dataset_version": run.dataset_version,
        "feature_version": run.feature_version,
        "metrics": run.metrics,
        "artifact_path": run.artifact_path,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
