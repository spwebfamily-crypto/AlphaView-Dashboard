from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import utc_now
from app.models.user import User
from app.models.withdrawal_request import WithdrawalRequest
from app.schemas.wallet import StripeConnectStatus
from app.services.stripe_service import StripeConnectService, StripeServiceError

WITHDRAWAL_STATUS_PENDING = "pending"
WITHDRAWAL_STATUS_REQUIRES_ONBOARDING = "requires_onboarding"
WITHDRAWAL_STATUS_PENDING_PAYOUT = "pending_payout"
WITHDRAWAL_STATUS_SUBMITTED = "submitted"
WITHDRAWAL_STATUS_FAILED = "failed"


class WalletServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _extract_requirements_status(account: dict) -> str | None:
    return (
        account.get("requirements", {})
        .get("summary", {})
        .get("minimum_deadline", {})
        .get("status")
    )


def _extract_capability_status(account: dict) -> str | None:
    return (
        account.get("configuration", {})
        .get("recipient", {})
        .get("capabilities", {})
        .get("stripe_balance", {})
        .get("stripe_transfers", {})
        .get("status")
    )


def build_stripe_status(user: User, account: dict | None = None) -> StripeConnectStatus:
    requirements_status = _extract_requirements_status(account or {})
    capability_status = _extract_capability_status(account or {})
    onboarding_complete = user.stripe_onboarding_complete
    transfers_enabled = user.stripe_transfers_enabled

    if account is not None:
        onboarding_complete = requirements_status not in {"currently_due", "past_due"}
        transfers_enabled = capability_status == "active"

    return StripeConnectStatus(
        account_id=user.stripe_connected_account_id,
        onboarding_complete=onboarding_complete,
        transfers_enabled=transfers_enabled,
        requirements_status=requirements_status,
        capability_status=capability_status,
        dashboard_access=bool(user.stripe_connected_account_id),
    )


def sync_user_stripe_status(db_session: Session, user: User, account: dict) -> StripeConnectStatus:
    status = build_stripe_status(user, account)
    user.stripe_onboarding_complete = status.onboarding_complete
    user.stripe_transfers_enabled = status.transfers_enabled
    db_session.commit()
    db_session.refresh(user)
    return status


def list_user_withdrawals(db_session: Session, user: User) -> list[WithdrawalRequest]:
    return list(
        db_session.scalars(
            select(WithdrawalRequest)
            .where(WithdrawalRequest.user_id == user.id)
            .order_by(WithdrawalRequest.created_at.desc())
        )
    )


def submit_withdrawal(
    db_session: Session,
    settings: Settings,
    stripe_service: StripeConnectService,
    *,
    user: User,
    amount_cents: int,
) -> WithdrawalRequest:
    if not settings.withdrawals_enabled:
        raise WalletServiceError(
            "Withdrawals are disabled by default. Enable them explicitly in the environment first.",
            status_code=403,
        )
    if amount_cents > user.withdrawable_balance_cents:
        raise WalletServiceError("Insufficient withdrawable balance.", status_code=422)
    if not user.stripe_connected_account_id:
        raise WalletServiceError("Complete Stripe onboarding before requesting a withdrawal.", status_code=409)

    request = WithdrawalRequest(
        user_id=user.id,
        amount_cents=amount_cents,
        currency=user.currency,
        status=WITHDRAWAL_STATUS_PENDING,
        stripe_account_id=user.stripe_connected_account_id,
    )
    db_session.add(request)
    db_session.flush()

    try:
        account = stripe_service.retrieve_connected_account(user.stripe_connected_account_id)
        status = sync_user_stripe_status(db_session, user, account)
        if not status.onboarding_complete or not status.transfers_enabled:
            request.status = WITHDRAWAL_STATUS_REQUIRES_ONBOARDING
            request.failure_message = "Stripe account requirements are still pending."
            db_session.commit()
            raise WalletServiceError(
                "Stripe onboarding is not complete. Finish the onboarding flow before withdrawing.",
                status_code=409,
            )

        balance = stripe_service.retrieve_platform_balance()
        available_amount = 0
        for entry in balance.get("available", []):
            if entry.get("currency") == user.currency:
                available_amount += int(entry.get("amount", 0))
        if available_amount < amount_cents:
            request.status = WITHDRAWAL_STATUS_FAILED
            request.failure_code = "insufficient_platform_balance"
            request.failure_message = "The platform Stripe balance is not sufficient for this withdrawal."
            db_session.commit()
            raise WalletServiceError(
                "The Stripe platform balance is not sufficient for this withdrawal yet.",
                status_code=409,
            )

        transfer = stripe_service.create_transfer(
            amount_cents=amount_cents,
            currency=user.currency,
            destination_account=user.stripe_connected_account_id,
            metadata={"withdrawal_request_id": request.id, "user_id": user.id},
        )
        request.stripe_transfer_id = transfer.get("id")
        request.status = WITHDRAWAL_STATUS_PENDING_PAYOUT
        user.withdrawable_balance_cents -= amount_cents
        db_session.commit()

        payout = stripe_service.create_connected_payout(
            account_id=user.stripe_connected_account_id,
            amount_cents=amount_cents,
            currency=user.currency,
            metadata={"withdrawal_request_id": request.id, "user_id": user.id},
        )
        request.stripe_payout_id = payout.get("id")
        request.status = WITHDRAWAL_STATUS_SUBMITTED
        request.processed_at = utc_now()
        db_session.commit()
        db_session.refresh(request)
        return request
    except StripeServiceError as exc:
        request.status = WITHDRAWAL_STATUS_FAILED
        request.failure_code = exc.code
        request.failure_message = exc.message
        db_session.commit()
        raise WalletServiceError(exc.message, status_code=exc.status_code) from exc
