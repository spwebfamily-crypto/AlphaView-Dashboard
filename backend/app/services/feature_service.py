from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.models.feature_row import FeatureRow
from app.models.market_bar import MarketDataBar
from app.models.symbol import Symbol
from app.services.market_data_service import ensure_symbol
from app.services.system_log_service import log_event
from app.utils.time import infer_session_flags


def _bars_to_frame(rows: Iterable[MarketDataBar]) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "timestamp": row.timestamp,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
            }
            for row in rows
        ]
    )
    if frame.empty:
        return frame
    return frame.sort_values("timestamp").reset_index(drop=True)


def build_feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return bars

    frame = bars.copy()
    frame["return_1"] = frame["close"].pct_change()
    frame["log_return_1"] = np.log(frame["close"]).diff()
    frame["sma_5"] = frame["close"].rolling(5).mean()
    frame["sma_20"] = frame["close"].rolling(20).mean()
    frame["ema_12"] = frame["close"].ewm(span=12, adjust=False).mean()
    frame["ema_26"] = frame["close"].ewm(span=26, adjust=False).mean()

    delta = frame["close"].diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    rs = gains / losses
    frame["rsi_14"] = 100 - (100 / (1 + rs))

    frame["macd"] = frame["ema_12"] - frame["ema_26"]
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()
    frame["macd_hist"] = frame["macd"] - frame["macd_signal"]

    prev_close = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr_14"] = tr.rolling(14).mean()

    frame["rolling_volatility_20"] = frame["return_1"].rolling(20).std()
    frame["volume_change"] = frame["volume"].pct_change()
    frame["relative_volume_20"] = frame["volume"] / frame["volume"].rolling(20).mean()
    frame["trend_strength"] = (frame["close"] / frame["sma_20"]) - 1

    session_flags = frame["timestamp"].apply(infer_session_flags)
    frame["is_premarket"] = session_flags.apply(lambda item: item[0])
    frame["is_regular_session"] = session_flags.apply(lambda item: item[1])
    frame["is_after_hours"] = session_flags.apply(lambda item: item[2])

    frame["volatility_bucket"] = np.select(
        [
            frame["rolling_volatility_20"] < 0.003,
            frame["rolling_volatility_20"] < 0.008,
        ],
        [0, 1],
        default=2,
    )
    frame["volume_bucket"] = np.select(
        [
            frame["relative_volume_20"] < 0.8,
            frame["relative_volume_20"] <= 1.2,
        ],
        [0, 1],
        default=2,
    )
    return frame


FEATURE_COLUMNS = [
    "return_1",
    "log_return_1",
    "sma_5",
    "sma_20",
    "ema_12",
    "ema_26",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr_14",
    "rolling_volatility_20",
    "volume_change",
    "relative_volume_20",
    "trend_strength",
    "is_premarket",
    "is_regular_session",
    "is_after_hours",
    "volatility_bucket",
    "volume_bucket",
    "bar_open",
    "bar_close",
    "bar_volume",
]


def materialize_features(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    pipeline_version: str,
) -> int:
    symbol_row: Symbol = ensure_symbol(session, symbol)
    symbol_id = symbol_row.id
    symbol_ticker = symbol_row.ticker
    bars = list(
        session.scalars(
            select(MarketDataBar)
            .where(
                and_(
                    MarketDataBar.symbol_id == symbol_id,
                    MarketDataBar.timeframe == timeframe,
                )
            )
            .order_by(MarketDataBar.timestamp.asc())
        )
    )
    bar_ids = [bar.id for bar in bars]
    frame = build_feature_frame(_bars_to_frame(bars))
    if frame.empty:
        return 0

    session.execute(
        delete(FeatureRow).where(
            and_(
                FeatureRow.symbol_id == symbol_id,
                FeatureRow.timeframe == timeframe,
                FeatureRow.pipeline_version == pipeline_version,
            )
        )
    )
    session.commit()
    session.expunge_all()

    for bar_id, (_, row) in zip(bar_ids, frame.iterrows(), strict=False):
        feature_payload = {
            "return_1": _nullable_float(row["return_1"]),
            "log_return_1": _nullable_float(row["log_return_1"]),
            "sma_5": _nullable_float(row["sma_5"]),
            "sma_20": _nullable_float(row["sma_20"]),
            "ema_12": _nullable_float(row["ema_12"]),
            "ema_26": _nullable_float(row["ema_26"]),
            "rsi_14": _nullable_float(row["rsi_14"]),
            "macd": _nullable_float(row["macd"]),
            "macd_signal": _nullable_float(row["macd_signal"]),
            "macd_hist": _nullable_float(row["macd_hist"]),
            "atr_14": _nullable_float(row["atr_14"]),
            "rolling_volatility_20": _nullable_float(row["rolling_volatility_20"]),
            "volume_change": _nullable_float(row["volume_change"]),
            "relative_volume_20": _nullable_float(row["relative_volume_20"]),
            "trend_strength": _nullable_float(row["trend_strength"]),
            "is_premarket": int(row["is_premarket"]),
            "is_regular_session": int(row["is_regular_session"]),
            "is_after_hours": int(row["is_after_hours"]),
            "volatility_bucket": int(row["volatility_bucket"]),
            "volume_bucket": int(row["volume_bucket"]),
            "bar_open": _nullable_float(row["open"]),
            "bar_close": _nullable_float(row["close"]),
            "bar_volume": _nullable_float(row["volume"]),
        }
        session.add(
                FeatureRow(
                    symbol_id=symbol_id,
                    source_bar_id=bar_id,
                    timeframe=timeframe,
                    timestamp=row["timestamp"],
                    pipeline_version=pipeline_version,
                    features=feature_payload,
                )
            )

    session.commit()
    log_event(
        session,
        level="INFO",
        source="features",
        event_type="features_materialized",
        message=f"Materialized features for {symbol_ticker} {timeframe}",
        context={
            "symbol": symbol_ticker,
            "timeframe": timeframe,
            "pipeline_version": pipeline_version,
            "rows": len(frame),
        },
    )
    return len(frame)


def get_feature_rows(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    pipeline_version: str = "v1",
    limit: int = 200,
) -> list[tuple[FeatureRow, str]]:
    symbol_row = ensure_symbol(session, symbol)
    rows = session.scalars(
        select(FeatureRow)
        .where(
            and_(
                FeatureRow.symbol_id == symbol_row.id,
                FeatureRow.timeframe == timeframe,
                FeatureRow.pipeline_version == pipeline_version,
            )
        )
        .order_by(FeatureRow.timestamp.asc())
        .limit(limit)
    )
    return [(row, symbol_row.ticker) for row in rows]


def feature_dataset_frame(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    pipeline_version: str,
) -> pd.DataFrame:
    symbol_row = ensure_symbol(session, symbol)
    rows = list(
        session.scalars(
            select(FeatureRow)
            .where(
                and_(
                    FeatureRow.symbol_id == symbol_row.id,
                    FeatureRow.timeframe == timeframe,
                    FeatureRow.pipeline_version == pipeline_version,
                )
            )
            .order_by(FeatureRow.timestamp.asc())
        )
    )
    bars = list(
        session.scalars(
            select(MarketDataBar)
            .where(
                and_(
                    MarketDataBar.symbol_id == symbol_row.id,
                    MarketDataBar.timeframe == timeframe,
                )
            )
            .order_by(MarketDataBar.timestamp.asc())
        )
    )
    feature_frame = pd.DataFrame([{"timestamp": row.timestamp, **row.features} for row in rows]).sort_values(
        "timestamp"
    )
    bar_frame = pd.DataFrame(
        [{"timestamp": row.timestamp, "close": float(row.close), "open": float(row.open)} for row in bars]
    ).sort_values("timestamp")
    if feature_frame.empty:
        return feature_frame
    return feature_frame.merge(bar_frame, on="timestamp", how="inner").reset_index(drop=True)


def _nullable_float(value: float | int | np.floating | np.integer | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
