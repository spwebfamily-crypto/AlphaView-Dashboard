from __future__ import annotations

import pandas as pd


def build_directional_labels(close_series: pd.Series, horizon: int = 1, threshold: float = 0.0) -> pd.Series:
    future_close = close_series.shift(-horizon)
    future_return = (future_close / close_series) - 1
    return (future_return > threshold).astype(int)

