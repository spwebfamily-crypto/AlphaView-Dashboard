from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_settings, require_active_user
from app.core.config import Settings
from app.models.user import User
from app.schemas.wallet import (
    StripeLinkResponse,
    WalletSummaryResponse,
    WithdrawalRequestCreate,
    WithdrawalRequestResponse,
)
from app.services.stripe_service import StripeConnectService
from app.services.wallet_service import (
    WalletServiceError,
    build_stripe_status,
    list_user_withdrawals,
    submit_withdrawal,
    sync_user_stripe_status,
)

router = APIRouter(prefix="/wallet")


@router.get("/summary", response_model=WalletSummaryResponse)
def get_wallet_summary(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> WalletSummaryResponse:
    stripe_status = build_stripe_status(current_user)
    if current_user.stripe_connected_account_id and settings.stripe_secret_key:
        try:
            account = StripeConnectService(settings).retrieve_connected_account(current_user.stripe_connected_account_id)
            stripe_status = sync_user_stripe_status(db_session, current_user, account)
        except Exception:
            stripe_status = build_stripe_status(current_user)

    return WalletSummaryResponse(
        withdrawable_balance_cents=current_user.withdrawable_balance_cents,
        currency=current_user.currency,
        withdrawals_enabled=settings.withdrawals_enabled,
        stripe=stripe_status,
    )


@router.get("/withdrawals", response_model=list[WithdrawalRequestResponse])
def list_withdrawals(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(require_active_user),
) -> list[WithdrawalRequestResponse]:
    return [WithdrawalRequestResponse.model_validate(item) for item in list_user_withdrawals(db_session, current_user)]


@router.post("/stripe/onboarding-link", response_model=StripeLinkResponse)
def create_onboarding_link(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> StripeLinkResponse:
    stripe_service = StripeConnectService(settings)
    if not stripe_service.enabled:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    try:
        if not current_user.stripe_connected_account_id:
            account = stripe_service.create_connected_account(
                email=current_user.email,
                display_name=current_user.full_name or current_user.email,
            )
            current_user.stripe_connected_account_id = account.get("id")
            current_user.stripe_onboarding_complete = False
            current_user.stripe_transfers_enabled = False
            db_session.commit()
            db_session.refresh(current_user)

        link = stripe_service.create_onboarding_link(current_user.stripe_connected_account_id)
    except Exception as exc:
        detail = getattr(exc, "message", str(exc))
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=detail) from exc

    return StripeLinkResponse(url=link["url"])


@router.post("/stripe/refresh", response_model=WalletSummaryResponse)
def refresh_stripe_status(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> WalletSummaryResponse:
    if not current_user.stripe_connected_account_id:
        raise HTTPException(status_code=404, detail="Stripe account not linked.")

    try:
        account = StripeConnectService(settings).retrieve_connected_account(current_user.stripe_connected_account_id)
        stripe_status = sync_user_stripe_status(db_session, current_user, account)
    except Exception as exc:
        detail = getattr(exc, "message", str(exc))
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=detail) from exc

    return WalletSummaryResponse(
        withdrawable_balance_cents=current_user.withdrawable_balance_cents,
        currency=current_user.currency,
        withdrawals_enabled=settings.withdrawals_enabled,
        stripe=stripe_status,
    )


@router.post("/stripe/dashboard-link", response_model=StripeLinkResponse)
def create_dashboard_link(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> StripeLinkResponse:
    if not current_user.stripe_connected_account_id:
        raise HTTPException(status_code=404, detail="Stripe account not linked.")

    try:
        link = StripeConnectService(settings).create_dashboard_link(current_user.stripe_connected_account_id)
    except Exception as exc:
        detail = getattr(exc, "message", str(exc))
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=detail) from exc

    return StripeLinkResponse(url=link["url"])


@router.post("/withdrawals", response_model=WithdrawalRequestResponse, status_code=status.HTTP_201_CREATED)
def create_withdrawal(
    payload: WithdrawalRequestCreate,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_active_user),
) -> WithdrawalRequestResponse:
    try:
        request = submit_withdrawal(
            db_session,
            settings,
            StripeConnectService(settings),
            user=current_user,
            amount_cents=payload.amount_cents,
        )
    except WalletServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return WithdrawalRequestResponse.model_validate(request)
