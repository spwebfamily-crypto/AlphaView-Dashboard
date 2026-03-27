from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillingSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    billing_status: str | None
    billing_plan_code: str | None
    billing_current_period_end: datetime | None
    checkout_ready: bool
    portal_ready: bool


class CheckoutSessionCreateRequest(BaseModel):
    price_id: str = Field(min_length=3, max_length=255)
    mode: Literal["payment", "subscription"] = "subscription"
    quantity: int = Field(default=1, ge=1, le=100)
    plan_code: str | None = Field(default=None, max_length=128)
    success_url: str | None = Field(default=None, max_length=2048)
    cancel_url: str | None = Field(default=None, max_length=2048)


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str


class BillingPortalSessionResponse(BaseModel):
    url: str


class BillingWebhookResponse(BaseModel):
    received: bool
    event_type: str
