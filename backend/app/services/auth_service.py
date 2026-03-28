from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    SecurityError,
    create_signed_token,
    decode_signed_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    utc_now,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.models.user_session import UserSession

ACCESS_COOKIE_NAME = "alphaview_access_token"
REFRESH_COOKIE_NAME = "alphaview_refresh_token"


class AuthServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class AuthSessionBundle:
    user: User
    session: UserSession
    access_token: str
    refresh_token: str


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def register_user(
    db_session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    full_name: str | None,
) -> User:
    if not settings.allow_public_registration:
        raise AuthServiceError("Public registration is disabled.", status_code=403)

    existing_user = db_session.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise AuthServiceError("An account with this email already exists.", status_code=409)

    try:
        validate_password_strength(password)
    except SecurityError as exc:
        raise AuthServiceError(str(exc), status_code=422) from exc

    password_hash, password_salt = hash_password(password)
    user = User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        password_salt=password_salt,
        role="member",
        currency=settings.withdrawals_currency,
        email_verified_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def authenticate_user(db_session: Session, email: str, password: str) -> User:
    user = db_session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash, user.password_salt):
        raise AuthServiceError("Invalid email or password.", status_code=401)
    if not user.is_active:
        raise AuthServiceError("This account is disabled.", status_code=403)
    return user


def issue_email_verification_code(
    db_session: Session,
    settings: Settings,
    *,
    user: User,
    force: bool = False,
) -> None:
    _ = (db_session, settings, user, force)
    raise AuthServiceError("Email verification is disabled for this deployment.", status_code=409)


def verify_email_code(
    db_session: Session,
    *,
    email: str,
    code: str,
) -> User:
    _ = (db_session, email, code)
    raise AuthServiceError("Email verification is disabled for this deployment. Sign in directly instead.", status_code=409)


def get_unverified_user_by_email(db_session: Session, email: str) -> User:
    _ = (db_session, email)
    raise AuthServiceError("Email verification is disabled for this deployment.", status_code=409)


def create_user_session(
    db_session: Session,
    settings: Settings,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthSessionBundle:
    refresh_token = generate_refresh_token()
    refresh_expiry = utc_now() + timedelta(days=settings.auth_refresh_token_ttl_days)
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=refresh_expiry,
        last_used_at=utc_now(),
    )
    db_session.add(session)
    db_session.flush()

    user.last_login_at = utc_now()
    access_token = create_signed_token(
        {"sub": user.id, "sid": session.id, "type": "access", "role": user.role},
        settings.auth_secret_key,
        timedelta(minutes=settings.auth_access_token_ttl_minutes),
    )
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(session)
    return AuthSessionBundle(
        user=user,
        session=session,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def rotate_user_session(
    db_session: Session,
    settings: Settings,
    *,
    refresh_token: str,
) -> AuthSessionBundle:
    session = db_session.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token))
    )
    if session is None or session.revoked_at is not None or _as_utc(session.expires_at) <= utc_now():
        raise AuthServiceError("Your session has expired. Please sign in again.", status_code=401)

    user = db_session.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AuthServiceError("This account is unavailable.", status_code=401)

    next_refresh_token = generate_refresh_token()
    session.refresh_token_hash = hash_token(next_refresh_token)
    session.last_used_at = utc_now()
    session.expires_at = utc_now() + timedelta(days=settings.auth_refresh_token_ttl_days)
    user.last_login_at = utc_now()

    access_token = create_signed_token(
        {"sub": user.id, "sid": session.id, "type": "access", "role": user.role},
        settings.auth_secret_key,
        timedelta(minutes=settings.auth_access_token_ttl_minutes),
    )
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(session)
    return AuthSessionBundle(
        user=user,
        session=session,
        access_token=access_token,
        refresh_token=next_refresh_token,
    )


def revoke_session_by_refresh_token(db_session: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    session = db_session.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token))
    )
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = utc_now()
    db_session.commit()


def resolve_user_from_access_token(
    db_session: Session,
    settings: Settings,
    access_token: str,
) -> User:
    try:
        payload = decode_signed_token(access_token, settings.auth_secret_key)
    except SecurityError as exc:
        raise AuthServiceError("Your session is invalid or expired.", status_code=401) from exc

    if payload.get("type") != "access":
        raise AuthServiceError("Invalid access token.", status_code=401)

    session_id = payload.get("sid")
    user_id = payload.get("sub")
    if not isinstance(session_id, int) or not isinstance(user_id, int):
        raise AuthServiceError("Invalid access token payload.", status_code=401)

    session = db_session.get(UserSession, session_id)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or _as_utc(session.expires_at) <= utc_now()
    ):
        raise AuthServiceError("Your session is invalid or expired.", status_code=401)

    user = db_session.get(User, user_id)
    if user is None:
        raise AuthServiceError("User not found.", status_code=401)
    return user
