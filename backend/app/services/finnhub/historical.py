from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.finnhub.client import FinnhubClient
from app.utils.time import ensure_utc


@dataclass(slots=True)
class FinnhubCandleBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def timeframe_to_finnhub_resolution(timeframe: str) -> str:
    normalized = timeframe.lower().strip()
    resolution = {
        "1min": "1",
        "5min": "5",
        "15min": "15",
        "30min": "30",
        "60min": "60",
        "1h": "60",
        "1day": "D",
    }.get(normalized)
    if resolution is None:
        raise ValueError(f"Unsupported Finnhub timeframe: {timeframe}")
    return resolution


def normalize_finnhub_candles(
    client: FinnhubClient,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[FinnhubCandleBar]:
    resolution = timeframe_to_finnhub_resolution(timeframe)
    normalized_start = ensure_utc(start)
    normalized_end = ensure_utc(end)
    bars_by_timestamp: dict[datetime, FinnhubCandleBar] = {}

    for window_start, window_end in build_request_windows(normalized_start, normalized_end, resolution):
        payload = client.get_stock_candles(
            symbol=symbol.upper(),
            resolution=resolution,
            start=window_start,
            end=window_end,
        )
        status = payload.get("s")
        if status == "no_data":
            continue
        if status != "ok":
            raise RuntimeError(f"Finnhub candle request failed for {symbol.upper()}: status={status}")

        timestamps = payload.get("t", [])
        opens = payload.get("o", [])
        highs = payload.get("h", [])
        lows = payload.get("l", [])
        closes = payload.get("c", [])
        volumes = payload.get("v", [])

        for index, unix_timestamp in enumerate(timestamps):
            timestamp = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
            bars_by_timestamp[timestamp] = FinnhubCandleBar(
                timestamp=timestamp,
                open=Decimal(str(opens[index])),
                high=Decimal(str(highs[index])),
                low=Decimal(str(lows[index])),
                close=Decimal(str(closes[index])),
                volume=int(volumes[index]),
            )

    return [bars_by_timestamp[timestamp] for timestamp in sorted(bars_by_timestamp)]


def build_request_windows(start: datetime, end: datetime, resolution: str) -> list[tuple[datetime, datetime]]:
    if resolution == "D":
        return [(start, end)]

    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    max_window = timedelta(days=28)

    while cursor < end:
        upper_bound = min(cursor + max_window, end)
        windows.append((cursor, upper_bound))
        if upper_bound >= end:
            break
        cursor = upper_bound + timedelta(seconds=1)

    return windows
