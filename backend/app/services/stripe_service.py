from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import Settings


class StripeServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _flatten_form_data(payload: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for key, value in payload.items():
        compound_key = f"{prefix}[{key}]" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_form_data(value, compound_key))
        elif value is not None:
            flattened[compound_key] = str(value)
    return flattened


class StripeConnectService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.stripe_secret_key)

    def _headers(
        self,
        *,
        api_version: str,
        stripe_account: str | None = None,
        json_request: bool = False,
    ) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.stripe_secret_key}",
            "Stripe-Version": api_version,
        }
        if stripe_account:
            headers["Stripe-Account"] = stripe_account
        if json_request:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        api_version: str,
        params: Iterable[tuple[str, str]] | None = None,
        json_payload: dict[str, Any] | None = None,
        form_payload: dict[str, Any] | None = None,
        stripe_account: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise StripeServiceError("Stripe is not configured for this environment.", status_code=503)

        url = f"{self.settings.stripe_api_base.rstrip('/')}{path}"
        headers = self._headers(
            api_version=api_version,
            stripe_account=stripe_account,
            json_request=json_payload is not None,
        )
        retries = 3
        for attempt in range(retries):
            try:
                with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                    response = client.request(
                        method,
                        url,
                        headers=headers,
                        params=list(params) if params is not None else None,
                        json=json_payload,
                        data=_flatten_form_data(form_payload or {}),
                    )
            except httpx.HTTPError as exc:
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise StripeServiceError("Stripe connection failed.", status_code=502) from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(0.35 * (attempt + 1))
                continue

            try:
                payload = response.json()
            except ValueError:
                payload = {"error": {"message": response.text or "Unknown Stripe error."}}

            if response.is_success:
                return payload

            error = payload.get("error", {})
            raise StripeServiceError(
                error.get("message", "Stripe request failed."),
                status_code=response.status_code,
                code=error.get("code"),
            )

        raise StripeServiceError("Stripe request failed after retries.", status_code=502)

    def create_connected_account(self, *, email: str, display_name: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v2/core/accounts",
            api_version=self.settings.stripe_connect_api_version,
            json_payload={
                "contact_email": email,
                "display_name": display_name,
                "defaults": {
                    "responsibilities": {
                        "fees_collector": "application",
                        "losses_collector": "application",
                    }
                },
                "dashboard": "express",
                "identity": {"country": "us", "entity_type": "individual"},
                "configuration": {
                    "recipient": {
                        "capabilities": {
                            "stripe_balance": {"stripe_transfers": {"requested": True}}
                        }
                    }
                },
                "include": ["configuration.recipient", "identity", "requirements"],
            },
        )

    def retrieve_connected_account(self, account_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/v2/core/accounts/{account_id}",
            api_version=self.settings.stripe_connect_api_version,
            params=[
                ("include", "configuration.recipient"),
                ("include", "identity"),
                ("include", "requirements"),
            ],
        )

    def create_onboarding_link(self, account_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v2/core/account_links",
            api_version=self.settings.stripe_account_links_api_version,
            json_payload={
                "account": account_id,
                "use_case": {
                    "type": "account_onboarding",
                    "account_onboarding": {
                        "configurations": ["recipient"],
                        "refresh_url": self.settings.stripe_connect_refresh_url_resolved,
                        "return_url": self.settings.stripe_connect_return_url_resolved,
                    },
                },
            },
        )

    def create_dashboard_link(self, account_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/accounts/{account_id}/login_links",
            api_version=self.settings.stripe_api_version,
            form_payload={},
        )

    def retrieve_platform_balance(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/balance",
            api_version=self.settings.stripe_api_version,
        )

    def create_transfer(
        self,
        *,
        amount_cents: int,
        currency: str,
        destination_account: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/transfers",
            api_version=self.settings.stripe_api_version,
            form_payload={
                "amount": amount_cents,
                "currency": currency,
                "destination": destination_account,
                "metadata": metadata or {},
            },
        )

    def create_connected_payout(
        self,
        *,
        account_id: str,
        amount_cents: int,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/payouts",
            api_version=self.settings.stripe_api_version,
            stripe_account=account_id,
            form_payload={
                "amount": amount_cents,
                "currency": currency,
                "method": "standard",
                "metadata": metadata or {},
            },
        )
