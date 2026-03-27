from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    currency: str
    withdrawable_balance_cents: int
    stripe_connected_account_id: str | None
    stripe_onboarding_complete: bool
    stripe_transfers_enabled: bool
    last_login_at: datetime | None


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse
    access_token_expires_in_seconds: int
    refresh_token_expires_in_seconds: int


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=256)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Invalid email address.")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Invalid email address.")
        return normalized


class MessageResponse(BaseModel):
    message: str
