from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.billing import BillingSummaryResponse
from app.services.stripe_service import StripeConnectService


class BillingServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _timestamp_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=UTC)


def _extract_plan_code_from_subscription(subscription: dict) -> str | None:
    metadata = subscription.get("metadata", {})
    if metadata.get("plan_code"):
        return str(metadata["plan_code"])

    items = subscription.get("items", {}).get("data", [])
    if not items:
        return None

    price = items[0].get("price", {})
    lookup_key = price.get("lookup_key")
    if lookup_key:
        return str(lookup_key)
    price_id = price.get("id")
    if price_id:
        return str(price_id)
    return None


def build_billing_summary(user: User, *, stripe_enabled: bool) -> BillingSummaryResponse:
    return BillingSummaryResponse(
        stripe_customer_id=user.stripe_customer_id,
        stripe_subscription_id=user.stripe_subscription_id,
        billing_status=user.billing_status,
        billing_plan_code=user.billing_plan_code,
        billing_current_period_end=user.billing_current_period_end,
        checkout_ready=stripe_enabled,
        portal_ready=stripe_enabled and bool(user.stripe_customer_id),
    )


def _find_user_by_customer_or_subscription(
    db_session: Session,
    *,
    customer_id: str | None = None,
    subscription_id: str | None = None,
) -> User | None:
    if customer_id:
        user = db_session.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user is not None:
            return user
    if subscription_id:
        return db_session.scalar(select(User).where(User.stripe_subscription_id == subscription_id))
    return None


def _find_user_for_checkout_session(db_session: Session, session_payload: dict) -> User | None:
    metadata = session_payload.get("metadata", {})
    user_id_raw = metadata.get("user_id") or session_payload.get("client_reference_id")
    if user_id_raw is not None:
        try:
            return db_session.get(User, int(user_id_raw))
        except (TypeError, ValueError):
            return None

    return _find_user_by_customer_or_subscription(
        db_session,
        customer_id=session_payload.get("customer"),
        subscription_id=session_payload.get("subscription"),
    )


def _find_user_for_subscription(db_session: Session, subscription_payload: dict) -> User | None:
    metadata = subscription_payload.get("metadata", {})
    user_id_raw = metadata.get("user_id")
    if user_id_raw is not None:
        try:
            return db_session.get(User, int(user_id_raw))
        except (TypeError, ValueError):
            return None

    return _find_user_by_customer_or_subscription(
        db_session,
        customer_id=subscription_payload.get("customer"),
        subscription_id=subscription_payload.get("id"),
    )


def _sync_subscription_fields(user: User, subscription_payload: dict) -> None:
    user.stripe_customer_id = subscription_payload.get("customer") or user.stripe_customer_id
    user.stripe_subscription_id = subscription_payload.get("id") or user.stripe_subscription_id
    user.billing_status = subscription_payload.get("status") or user.billing_status
    user.billing_plan_code = _extract_plan_code_from_subscription(subscription_payload) or user.billing_plan_code
    user.billing_current_period_end = _timestamp_to_datetime(subscription_payload.get("current_period_end"))


def _sync_checkout_session_completed(
    db_session: Session,
    stripe_service: StripeConnectService,
    session_payload: dict,
) -> None:
    user = _find_user_for_checkout_session(db_session, session_payload)
    if user is None:
        return

    user.stripe_customer_id = session_payload.get("customer") or user.stripe_customer_id
    user.billing_last_checkout_session_id = session_payload.get("id") or user.billing_last_checkout_session_id

    metadata = session_payload.get("metadata", {})
    if metadata.get("plan_code"):
        user.billing_plan_code = str(metadata["plan_code"])

    if session_payload.get("mode") == "subscription" and session_payload.get("subscription"):
        subscription = stripe_service.retrieve_subscription(str(session_payload["subscription"]))
        _sync_subscription_fields(user, subscription)
    else:
        user.billing_status = str(session_payload.get("payment_status") or "completed")
        user.billing_current_period_end = None
        user.stripe_subscription_id = None

    db_session.commit()
    db_session.refresh(user)


def _sync_subscription_payload(db_session: Session, subscription_payload: dict) -> None:
    user = _find_user_for_subscription(db_session, subscription_payload)
    if user is None:
        return

    _sync_subscription_fields(user, subscription_payload)
    db_session.commit()
    db_session.refresh(user)


def _sync_invoice_payload(
    db_session: Session,
    stripe_service: StripeConnectService,
    invoice_payload: dict,
) -> None:
    subscription_id = invoice_payload.get("subscription")
    customer_id = invoice_payload.get("customer")
    user = _find_user_by_customer_or_subscription(
        db_session,
        customer_id=customer_id,
        subscription_id=subscription_id,
    )
    if user is None:
        return

    if subscription_id:
        subscription = stripe_service.retrieve_subscription(str(subscription_id))
        _sync_subscription_fields(user, subscription)
    else:
        user.stripe_customer_id = customer_id or user.stripe_customer_id
        user.billing_status = str(invoice_payload.get("status") or user.billing_status or "paid")

    db_session.commit()
    db_session.refresh(user)


def _sync_subscription_deleted(db_session: Session, subscription_payload: dict) -> None:
    user = _find_user_for_subscription(db_session, subscription_payload)
    if user is None:
        return

    user.stripe_customer_id = subscription_payload.get("customer") or user.stripe_customer_id
    user.stripe_subscription_id = subscription_payload.get("id") or user.stripe_subscription_id
    user.billing_status = subscription_payload.get("status") or "canceled"
    user.billing_current_period_end = _timestamp_to_datetime(subscription_payload.get("current_period_end"))
    db_session.commit()
    db_session.refresh(user)


def process_billing_webhook(
    db_session: Session,
    stripe_service: StripeConnectService,
    event: dict,
) -> str:
    event_type = str(event.get("type") or "unknown")
    payload = event.get("data", {}).get("object", {})
    if not isinstance(payload, dict):
        return event_type

    if event_type == "checkout.session.completed":
        _sync_checkout_session_completed(db_session, stripe_service, payload)
    elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        _sync_subscription_payload(db_session, payload)
    elif event_type == "customer.subscription.deleted":
        _sync_subscription_deleted(db_session, payload)
    elif event_type in {"invoice.payment_succeeded", "invoice.payment_failed"}:
        _sync_invoice_payload(db_session, stripe_service, payload)

    return event_type
