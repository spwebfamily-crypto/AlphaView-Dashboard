from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import StripeConnectMode
from app.models.user import User
from app.services.stripe_service import StripeConnectService, StripeServiceError


def test_protected_routes_require_authentication(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_creates_verified_session_and_allows_direct_login(
    client,
    db_session: Session,
) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "pending@example.com",
            "password": "Password123!",
            "full_name": "Pending User",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["user"]["email"] == "pending@example.com"

    user = db_session.scalar(select(User).where(User.email == "pending@example.com"))
    assert user is not None
    assert user.email_verified_at is not None
    assert user.email_verification_code_hash is None

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "pending@example.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "pending@example.com"

    db_session.refresh(user)
    assert user.email_verified_at is not None
    assert user.email_verification_code_hash is None


def test_verification_endpoints_are_disabled(client) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "resend@example.com",
            "password": "Password123!",
            "full_name": "Resend User",
        },
    )
    assert register_response.status_code == 201
    resend_response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert resend_response.status_code == 409
    assert resend_response.json()["detail"] == "Email verification is disabled for this deployment."

    verify_response = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "resend@example.com", "code": "123456"},
    )
    assert verify_response.status_code == 409
    assert verify_response.json()["detail"] == "Email verification is disabled for this deployment. Sign in directly instead."


def test_auth_session_can_refresh_and_logout(authenticated_client) -> None:
    me_response = authenticated_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "trader@example.com"

    refresh_response = authenticated_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200

    logout_response = authenticated_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    protected_response = authenticated_client.get("/api/v1/auth/me")
    assert protected_response.status_code == 401


def test_wallet_can_create_stripe_onboarding_link(authenticated_client, db_session: Session, monkeypatch) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"

    monkeypatch.setattr(
        StripeConnectService,
        "create_connected_account",
        lambda self, email, display_name: {"id": "acct_test_connect"},
    )
    monkeypatch.setattr(
        StripeConnectService,
        "create_onboarding_link",
        lambda self, account_id: {"url": "https://connect.stripe.test/onboarding"},
    )

    response = authenticated_client.post("/api/v1/wallet/stripe/onboarding-link")
    assert response.status_code == 200
    assert response.json()["url"] == "https://connect.stripe.test/onboarding"

    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    assert user.stripe_connected_account_id == "acct_test_connect"


def test_stripe_connect_auto_falls_back_to_v1_when_accounts_v2_is_unavailable(test_settings, monkeypatch) -> None:
    test_settings.stripe_secret_key = "sk_test_example"
    test_settings.stripe_connect_mode = StripeConnectMode.AUTO
    stripe_service = StripeConnectService(test_settings)
    request_paths: list[str] = []

    def fake_request(self, method, path, **kwargs):
        request_paths.append(path)
        if path == "/v2/core/accounts":
            raise StripeServiceError(
                "Accounts v2 is not enabled for your platform. If you're interested in using this API with your integration, please visit https://docs.stripe.com/connect/accounts-v2.",
                status_code=400,
            )
        if path == "/v1/accounts":
            return {"id": "acct_test_connect"}
        if path == "/v1/account_links":
            return {"url": "https://connect.stripe.test/onboarding"}
        raise AssertionError(f"Unexpected Stripe path: {path}")

    monkeypatch.setattr(StripeConnectService, "_request", fake_request)

    account = stripe_service.create_connected_account(email="trader@example.com", display_name="Trader Test")
    link = stripe_service.create_onboarding_link(account["id"])

    assert account["id"] == "acct_test_connect"
    assert link["url"] == "https://connect.stripe.test/onboarding"
    assert request_paths == ["/v2/core/accounts", "/v1/accounts", "/v1/account_links"]


def test_wallet_summary_supports_stripe_v1_account_payload(
    authenticated_client,
    db_session: Session,
    monkeypatch,
) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"

    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    user.stripe_connected_account_id = "acct_test_connect"
    db_session.commit()

    monkeypatch.setattr(
        StripeConnectService,
        "retrieve_connected_account",
        lambda self, account_id: {
            "requirements": {
                "currently_due": [],
                "past_due": [],
                "eventually_due": [],
                "disabled_reason": None,
            },
            "capabilities": {"transfers": "active"},
            "payouts_enabled": True,
        },
    )

    response = authenticated_client.get("/api/v1/wallet/summary")

    assert response.status_code == 200
    payload = response.json()["stripe"]
    assert payload["account_id"] == "acct_test_connect"
    assert payload["onboarding_complete"] is True
    assert payload["transfers_enabled"] is True
    assert payload["requirements_status"] == "complete"
    assert payload["capability_status"] == "active"


def test_wallet_onboarding_returns_actionable_connect_activation_message(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"

    def raise_connect_not_enabled(self, email, display_name):
        raise StripeServiceError(
            "You can only create new accounts if you've signed up for Connect, which you can do at https://dashboard.stripe.com/connect.",
            status_code=400,
        )

    monkeypatch.setattr(StripeConnectService, "create_connected_account", raise_connect_not_enabled)

    response = authenticated_client.post("/api/v1/wallet/stripe/onboarding-link")

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Stripe Connect ainda nao esta ativado nesta conta. Ative em https://dashboard.stripe.com/connect e tente novamente."
    )


def test_wallet_withdrawal_submits_transfer_and_payout(
    authenticated_client,
    db_session: Session,
    monkeypatch,
) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"
    authenticated_client.app.state.settings.withdrawals_enabled = True

    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    user.withdrawable_balance_cents = 50_000
    user.currency = "usd"
    user.stripe_connected_account_id = "acct_test_connect"
    user.stripe_onboarding_complete = True
    user.stripe_transfers_enabled = True
    db_session.commit()

    monkeypatch.setattr(
        StripeConnectService,
        "retrieve_connected_account",
        lambda self, account_id: {
            "configuration": {
                "recipient": {
                    "capabilities": {
                        "stripe_balance": {"stripe_transfers": {"status": "active"}}
                    }
                }
            },
            "requirements": {"summary": {"minimum_deadline": {"status": "eventually_due"}}},
        },
    )
    monkeypatch.setattr(
        StripeConnectService,
        "retrieve_platform_balance",
        lambda self: {"available": [{"currency": "usd", "amount": 100_000}]},
    )
    monkeypatch.setattr(
        StripeConnectService,
        "create_transfer",
        lambda self, amount_cents, currency, destination_account, metadata=None: {"id": "tr_test_123"},
    )
    monkeypatch.setattr(
        StripeConnectService,
        "create_connected_payout",
        lambda self, account_id, amount_cents, currency, metadata=None: {"id": "po_test_123"},
    )

    response = authenticated_client.post("/api/v1/wallet/withdrawals", json={"amount_cents": 25_000})
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "submitted"
    assert payload["stripe_transfer_id"] == "tr_test_123"
    assert payload["stripe_payout_id"] == "po_test_123"

    db_session.refresh(user)
    assert user.withdrawable_balance_cents == 25_000
