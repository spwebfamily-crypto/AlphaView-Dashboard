from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from time import sleep

from app.core.config import Settings


class PolygonClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.polygon_api_key:
            raise RuntimeError("POLYGON_API_KEY is not configured.")

        request_params = {**params, "apiKey": self.settings.polygon_api_key}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                    response = client.get(f"{self.settings.polygon_base_url}{path}", params=request_params)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                status_code = exc.response.status_code
                if status_code == 429:
                    raise RuntimeError("Polygon rate limit reached. Falling back to cached or preview data.") from exc
                raise RuntimeError(f"Polygon request failed with status {status_code}.") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                raise RuntimeError("Polygon connection failed.") from exc

        if last_error is not None:
            raise RuntimeError("Polygon request failed after retries.") from last_error
        raise RuntimeError("Polygon request failed.")

    def get_aggregates(
        self,
        *,
        symbol: str,
        multiplier: int,
        timespan: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        payload = self._get(
            (
                f"/v2/aggs/ticker/{symbol}/range/"
                f"{multiplier}/{timespan}/{start.date().isoformat()}/{end.date().isoformat()}"
            ),
            params={
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
            },
        )
        return payload.get("results", [])

    def list_reference_tickers(
        self,
        *,
        locale: str = "us",
        market: str = "stocks",
        active: bool = True,
        limit: int = 50,
        search: str | None = None,
        exchange: str | None = None,
        security_type: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "locale": locale,
            "market": market,
            "active": str(active).lower(),
            "limit": max(1, min(limit, 1000)),
            "sort": "ticker",
            "order": "asc",
        }
        if search:
            params["search"] = search
        if exchange:
            params["exchange"] = exchange
        if security_type:
            params["type"] = security_type
        if cursor:
            params["cursor"] = cursor

        return self._get("/v3/reference/tickers", params=params)
