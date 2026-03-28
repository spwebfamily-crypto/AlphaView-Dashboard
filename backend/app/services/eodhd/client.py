from __future__ import annotations

from datetime import date, datetime
from time import sleep
from typing import Any

import httpx

from app.core.config import Settings


class EodhdClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(self, *, query: str, limit: int = 50) -> list[dict[str, Any]]:
        payload = self._request(f"/search/{query.upper()}", params={"limit": max(1, min(limit, 100))})
        return payload if isinstance(payload, list) else []

    def list_exchange_symbols(self, *, exchange: str) -> list[dict[str, Any]]:
        payload = self._request(f"/exchange-symbol-list/{exchange.upper()}", params={})
        return payload if isinstance(payload, list) else []

    def get_real_time_quotes(self, *, symbols: list[str]) -> list[dict[str, Any]]:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if not normalized_symbols:
            return []

        primary_symbol, *extra_symbols = normalized_symbols
        params: dict[str, Any] = {}
        if extra_symbols:
            params["s"] = ",".join(extra_symbols)

        payload = self._request(f"/real-time/{primary_symbol}", params=params)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        return []

    def get_eod_bars(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        payload = self._request(
            f"/eod/{symbol.upper()}",
            params={
                "from": start.date().isoformat(),
                "to": end.date().isoformat(),
            },
        )
        return payload if isinstance(payload, list) else []

    def _request(self, path: str, *, params: dict[str, Any]) -> Any:
        if not self.settings.eodhd_api_token:
            raise RuntimeError("EODHD_API_TOKEN is not configured.")

        request_params = {**params, "api_token": self.settings.eodhd_api_token, "fmt": "json"}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                    response = client.get(f"{self.settings.eodhd_base_url.rstrip('/')}{path}", params=request_params)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                if status_code == 403:
                    raise RuntimeError(
                        "EODHD rejected this request with HTTP 403. This token does not cover the requested endpoint or market."
                    ) from exc
                if status_code == 404:
                    raise RuntimeError("EODHD did not find the requested symbol or exchange.") from exc
                raise RuntimeError(f"EODHD request failed with status {status_code}.") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < 2:
                    sleep(0.4 * (attempt + 1))
                    continue
                raise RuntimeError("EODHD connection failed.") from exc

        if last_error is not None:
            raise RuntimeError("EODHD request failed after retries.") from last_error
        raise RuntimeError("EODHD request failed.")
