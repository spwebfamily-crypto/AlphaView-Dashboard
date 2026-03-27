from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings


class PolygonClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_aggregates(
        self,
        *,
        symbol: str,
        multiplier: int,
        timespan: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        if not self.settings.polygon_api_key:
            raise RuntimeError("POLYGON_API_KEY is not configured.")

        url = (
            f"{self.settings.polygon_base_url}/v2/aggs/ticker/{symbol}/range/"
            f"{multiplier}/{timespan}/{start.date().isoformat()}/{end.date().isoformat()}"
        )
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self.settings.polygon_api_key,
        }
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        return payload.get("results", [])

