from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from app.services.market_data_service import NormalizedBar, generate_synthetic_bars


def preview_stream(
    symbols: Iterable[str], timeframe: str = "1min", points: int = 20
) -> dict[str, list[NormalizedBar]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=max(points, 5))
    return {
        symbol: generate_synthetic_bars(symbol=symbol, timeframe=timeframe, start=start, end=end)[
            -points:
        ]
        for symbol in symbols
    }

