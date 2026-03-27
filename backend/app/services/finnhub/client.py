from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings


class FinnhubClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_stock_candles(
        self,
        *,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        return self._request(
            "/stock/candle",
            {
                "symbol": symbol,
                "resolution": resolution,
                "from": int(start.timestamp()),
                "to": int(end.timestamp()),
            },
        )

    def get_quote(self, *, symbol: str) -> dict[str, Any]:
        return self._request("/quote", {"symbol": symbol})

    def get_market_status(self, *, exchange: str) -> dict[str, Any]:
        return self._request("/stock/market-status", {"exchange": exchange})

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.finnhub_api_key:
            raise RuntimeError("FINNHUB_API_KEY is not configured.")

        request_params = {**params, "token": self.settings.finnhub_api_key}
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.get(f"{self.settings.finnhub_base_url}{path}", params=request_params)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403 and path == "/stock/candle":
                    raise RuntimeError(
                        "Finnhub rejected the candle request with HTTP 403. Historical candles may require a paid "
                        "Finnhub market-data plan for this API key."
                    ) from exc
                raise RuntimeError(
                    f"Finnhub request failed for {path} with HTTP {exc.response.status_code}."
                ) from exc
            return response.json()
