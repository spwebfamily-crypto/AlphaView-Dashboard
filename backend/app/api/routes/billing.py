from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_settings, require_active_user
from app.core.config import Settings
from app.models.user import User
from app.schemas.billing import (
    BillingPortalSessionResponse,
    BillingSummaryResponse,
    BillingWebhookResponse,
    CheckoutSessionCreateRequest,
    CheckoutSessionResponse,
)
from app.services.billing_service import BillingServiceError, build_billing_summary, process_billing_webhook
from app.services.stripe_service import StripeConnectService, StripeServiceError

router = APIRouter(prefix="/billing")


@router.get("/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> BillingSummaryResponse:
    return build_billing_summary(current_user, stripe_enabled=bool(settings.stripe_secret_key))


@router.post(
    "/checkout-session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout_session(
    payload: CheckoutSessionCreateRequest,
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> CheckoutSessionResponse:
    stripe_service = StripeConnectService(settings)
    if not stripe_service.enabled:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    try:
        session = stripe_service.create_checkout_session(
            customer_id=current_user.stripe_customer_id,
            customer_email=None if current_user.stripe_customer_id else current_user.email,
            client_reference_id=str(current_user.id),
            price_id=payload.price_id,
            mode=payload.mode,
            quantity=payload.quantity,
            metadata={
                "user_id": current_user.id,
                "user_email": current_user.email,
                "plan_code": payload.plan_code,
                "mode": payload.mode,
                "price_id": payload.price_id,
            },
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except StripeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return CheckoutSessionResponse(session_id=session["id"], url=session["url"])


@router.post("/portal-session", response_model=BillingPortalSessionResponse)
def create_billing_portal_session(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> BillingPortalSessionResponse:
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=409, detail="No Stripe customer is linked to this account yet.")

    stripe_service = StripeConnectService(settings)
    if not stripe_service.enabled:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    try:
        session = stripe_service.create_billing_portal_session(customer_id=current_user.stripe_customer_id)
    except StripeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return BillingPortalSessionResponse(url=session["url"])


@router.post("/webhook", response_model=BillingWebhookResponse)
async def handle_billing_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> BillingWebhookResponse:
    stripe_service = StripeConnectService(settings)
    try:
        event = stripe_service.parse_webhook_event(await request.body(), stripe_signature)
        event_type = process_billing_webhook(db_session, stripe_service, event)
    except (StripeServiceError, BillingServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return BillingWebhookResponse(received=True, event_type=event_type)
