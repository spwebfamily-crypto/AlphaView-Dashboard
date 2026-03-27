from __future__ import annotations

import hashlib
import hmac
import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.stripe_service import StripeConnectService


def _stripe_signature(secret: str, payload: bytes) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_billing_checkout_session_can_be_created(authenticated_client, monkeypatch) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"
    captured: dict[str, object] = {}

    def fake_create_checkout_session(self, **kwargs):
        captured.update(kwargs)
        return {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}

    monkeypatch.setattr(StripeConnectService, "create_checkout_session", fake_create_checkout_session)

    response = authenticated_client.post(
        "/api/v1/billing/checkout-session",
        json={
            "price_id": "price_test_basic",
            "mode": "subscription",
            "quantity": 1,
            "plan_code": "starter",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "session_id": "cs_test_123",
        "url": "https://checkout.stripe.test/session",
    }
    assert captured["price_id"] == "price_test_basic"
    assert captured["mode"] == "subscription"
    assert captured["customer_email"] == "trader@example.com"
    assert captured["metadata"] == {
        "user_id": 1,
        "user_email": "trader@example.com",
        "plan_code": "starter",
        "mode": "subscription",
        "price_id": "price_test_basic",
    }


def test_billing_portal_session_uses_existing_customer(authenticated_client, db_session: Session, monkeypatch) -> None:
    authenticated_client.app.state.settings.stripe_secret_key = "sk_test_example"
    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    user.stripe_customer_id = "cus_test_123"
    db_session.commit()

    monkeypatch.setattr(
        StripeConnectService,
        "create_billing_portal_session",
        lambda self, customer_id: {"url": f"https://billing.stripe.test/{customer_id}"},
    )

    response = authenticated_client.post("/api/v1/billing/portal-session")
    assert response.status_code == 200
    assert response.json()["url"] == "https://billing.stripe.test/cus_test_123"


def test_billing_webhook_syncs_completed_subscription_checkout(
    authenticated_client,
    db_session: Session,
    monkeypatch,
) -> None:
    settings = authenticated_client.app.state.settings
    settings.stripe_secret_key = "sk_test_example"
    settings.stripe_webhook_secret = "whsec_test_example"

    def fake_retrieve_subscription(self, subscription_id: str) -> dict:
        assert subscription_id == "sub_test_123"
        return {
            "id": "sub_test_123",
            "customer": "cus_test_123",
            "status": "active",
            "current_period_end": 1_800_000_000,
            "metadata": {"plan_code": "starter", "user_id": "1"},
            "items": {"data": [{"price": {"id": "price_test_basic"}}]},
        }

    monkeypatch.setattr(StripeConnectService, "retrieve_subscription", fake_retrieve_subscription)

    payload = {
        "id": "evt_test_checkout_completed",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "client_reference_id": "1",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "mode": "subscription",
                "payment_status": "paid",
                "metadata": {"user_id": "1", "plan_code": "starter"},
            }
        },
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    response = authenticated_client.post(
        "/api/v1/billing/webhook",
        content=raw_payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": _stripe_signature(settings.stripe_webhook_secret, raw_payload),
        },
    )
    assert response.status_code == 200
    assert response.json() == {"received": True, "event_type": "checkout.session.completed"}

    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    assert user.stripe_customer_id == "cus_test_123"
    assert user.stripe_subscription_id == "sub_test_123"
    assert user.billing_status == "active"
    assert user.billing_plan_code == "starter"
    assert user.billing_last_checkout_session_id == "cs_test_123"
    assert user.billing_current_period_end is not None


def test_billing_webhook_marks_subscription_deleted(authenticated_client, db_session: Session) -> None:
    settings = authenticated_client.app.state.settings
    settings.stripe_secret_key = "sk_test_example"
    settings.stripe_webhook_secret = "whsec_test_example"

    user = db_session.scalar(select(User).where(User.email == "trader@example.com"))
    assert user is not None
    user.stripe_customer_id = "cus_test_123"
    user.stripe_subscription_id = "sub_test_123"
    user.billing_status = "active"
    db_session.commit()

    payload = {
        "id": "evt_test_subscription_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_123",
                "status": "canceled",
                "current_period_end": 1_800_000_500,
            }
        },
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    response = authenticated_client.post(
        "/api/v1/billing/webhook",
        content=raw_payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": _stripe_signature(settings.stripe_webhook_secret, raw_payload),
        },
    )
    assert response.status_code == 200

    db_session.refresh(user)
    assert user.billing_status == "canceled"
    assert user.stripe_subscription_id == "sub_test_123"
    assert user.billing_current_period_end is not None
