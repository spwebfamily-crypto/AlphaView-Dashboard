from collections.abc import Generator

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import User
from app.services.auth_service import ACCESS_COOKIE_NAME, AuthServiceError, resolve_user_from_access_token


def get_db_session(request: Request) -> Generator[Session, None, None]:
    yield from request.app.state.session_manager.get_session()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_user(
    request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    access_token_cookie: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
) -> User:
    access_token = access_token_cookie or _extract_bearer_token(authorization)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    try:
        return resolve_user_from_access_token(db_session, settings, access_token)
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def require_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")
    return user

