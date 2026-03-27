from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StripeConnectStatus(BaseModel):
    account_id: str | None = None
    onboarding_complete: bool = False
    transfers_enabled: bool = False
    requirements_status: str | None = None
    capability_status: str | None = None
    dashboard_access: bool = False


class WalletSummaryResponse(BaseModel):
    withdrawable_balance_cents: int
    currency: str
    withdrawals_enabled: bool
    stripe: StripeConnectStatus


class StripeLinkResponse(BaseModel):
    url: str


class WithdrawalRequestCreate(BaseModel):
    amount_cents: int = Field(gt=0)


class WithdrawalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_cents: int
    currency: str
    status: str
    stripe_account_id: str | None
    stripe_transfer_id: str | None
    stripe_payout_id: str | None
    failure_code: str | None
    failure_message: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime
