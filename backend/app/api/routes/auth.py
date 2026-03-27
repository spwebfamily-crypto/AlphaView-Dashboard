from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_settings, require_active_user
from app.core.config import Settings
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    AuthUserResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    AuthServiceError,
    AuthSessionBundle,
    authenticate_user,
    create_user_session,
    get_unverified_user_by_email,
    issue_email_verification_code,
    register_user,
    revoke_session_by_refresh_token,
    rotate_user_session,
    verify_email_code,
)
from app.services.email_service import EmailDeliveryError, SmtpEmailService

router = APIRouter(prefix="/auth")


def _set_auth_cookies(response: Response, settings: Settings, bundle: AuthSessionBundle) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        bundle.access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_access_token_ttl_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        bundle.refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_refresh_token_ttl_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")


def _serialize_auth_response(bundle: AuthSessionBundle, settings: Settings) -> AuthSessionResponse:
    return AuthSessionResponse(
        user=AuthUserResponse.model_validate(bundle.user),
        access_token_expires_in_seconds=settings.auth_access_token_ttl_minutes * 60,
        refresh_token_expires_in_seconds=settings.auth_refresh_token_ttl_days * 24 * 60 * 60,
    )


def _serialize_register_response(user: User, settings: Settings) -> RegisterResponse:
    return RegisterResponse(
        message=f"A confirmation code was sent to {user.email}.",
        email=user.email,
        verification_expires_in_seconds=settings.auth_verification_code_ttl_minutes * 60,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RegisterResponse:
    user: User | None = None
    try:
        user = register_user(
            db_session,
            settings,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        challenge = issue_email_verification_code(db_session, settings, user=user)
        SmtpEmailService(settings).send_verification_code(
            recipient_email=user.email,
            recipient_name=user.full_name,
            code=challenge.code,
            ttl_minutes=settings.auth_verification_code_ttl_minutes,
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except EmailDeliveryError as exc:
        if user is not None:
            user.email_verification_sent_at = None
            db_session.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return _serialize_register_response(user, settings)


@router.post("/verify-email", response_model=AuthSessionResponse)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    try:
        user = verify_email_code(db_session, email=payload.email, code=payload.code)
        bundle = create_user_session(
            db_session,
            settings,
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    _set_auth_cookies(response, settings, bundle)
    return _serialize_auth_response(bundle, settings)


@router.post("/resend-verification", response_model=RegisterResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RegisterResponse:
    user: User | None = None
    try:
        user = get_unverified_user_by_email(db_session, payload.email)
        challenge = issue_email_verification_code(db_session, settings, user=user)
        SmtpEmailService(settings).send_verification_code(
            recipient_email=user.email,
            recipient_name=user.full_name,
            code=challenge.code,
            ttl_minutes=settings.auth_verification_code_ttl_minutes,
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except EmailDeliveryError as exc:
        if user is not None:
            user.email_verification_sent_at = None
            db_session.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return _serialize_register_response(user, settings)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    try:
        user = authenticate_user(db_session, payload.email, payload.password)
        bundle = create_user_session(
            db_session,
            settings,
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    _set_auth_cookies(response, settings, bundle)
    return _serialize_auth_response(bundle, settings)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh_session(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    try:
        bundle = rotate_user_session(db_session, settings, refresh_token=refresh_token_cookie or "")
    except AuthServiceError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    _set_auth_cookies(response, settings, bundle)
    return _serialize_auth_response(bundle, settings)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db_session: Session = Depends(get_db_session),
) -> MessageResponse:
    revoke_session_by_refresh_token(db_session, refresh_token_cookie)
    _clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: User = Depends(require_active_user)) -> AuthUserResponse:
    return AuthUserResponse.model_validate(current_user)
