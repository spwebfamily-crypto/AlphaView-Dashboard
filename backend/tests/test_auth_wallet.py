from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.stripe_service import StripeConnectService


def test_protected_routes_require_authentication(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


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
