from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from app.services.market_data_service import NormalizedBar, generate_synthetic_bars


def preview_stream(
    symbols: Iterable[str], timeframe: str = "1min", points: int = 20
) -> dict[str, list[NormalizedBar]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=2)
    preview_by_symbol: dict[str, list[NormalizedBar]] = {}

    for symbol in symbols:
        bars = generate_synthetic_bars(symbol=symbol, timeframe=timeframe, start=start, end=end)
        expansion_days = 2
        while len(bars) < points and expansion_days <= 14:
            expansion_days += 2
            bars = generate_synthetic_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=end - timedelta(days=expansion_days),
                end=end,
            )
        preview_by_symbol[symbol] = bars[-points:]
    return preview_by_symbol
