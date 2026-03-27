from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.services.polygon.client import PolygonClient


@dataclass(slots=True)
class PolygonAggregateBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal | None
    trades_count: int | None


def normalize_polygon_aggregates(
    client: PolygonClient,
    *,
    symbol: str,
    multiplier: int,
    timespan: str,
    start: datetime,
    end: datetime,
) -> list[PolygonAggregateBar]:
    results = client.get_aggregates(
        symbol=symbol,
        multiplier=multiplier,
        timespan=timespan,
        start=start,
        end=end,
    )
    return [normalize_polygon_result(item) for item in results]


def normalize_polygon_result(payload: dict[str, Any]) -> PolygonAggregateBar:
    return PolygonAggregateBar(
        timestamp=datetime.fromtimestamp(payload["t"] / 1000, tz=timezone.utc),
        open=Decimal(str(payload["o"])),
        high=Decimal(str(payload["h"])),
        low=Decimal(str(payload["l"])),
        close=Decimal(str(payload["c"])),
        volume=int(payload["v"]),
        vwap=Decimal(str(payload["vw"])) if payload.get("vw") is not None else None,
        trades_count=int(payload["n"]) if payload.get("n") is not None else None,
    )

