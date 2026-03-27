from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any


class SecurityError(ValueError):
    """Raised when a security primitive cannot be validated."""


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt_bytes = secrets.token_bytes(16) if salt is None else base64.urlsafe_b64decode(f"{salt}==")
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 600_000)
    password_hash = base64.urlsafe_b64encode(derived_key).decode("utf-8").rstrip("=")
    encoded_salt = base64.urlsafe_b64encode(salt_bytes).decode("utf-8").rstrip("=")
    return password_hash, encoded_salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def validate_password_strength(password: str) -> None:
    checks = [
        (len(password) >= 10, "Password must contain at least 10 characters."),
        (any(char.islower() for char in password), "Password must include a lowercase letter."),
        (any(char.isupper() for char in password), "Password must include an uppercase letter."),
        (any(char.isdigit() for char in password), "Password must include a number."),
        (
            any(not char.isalnum() for char in password),
            "Password must include a special character.",
        ),
    ]
    errors = [message for passed, message in checks if not passed]
    if errors:
        raise SecurityError(" ".join(errors))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_verification_code(length: int = 6) -> str:
    upper_bound = 10**length
    return f"{secrets.randbelow(upper_bound):0{length}d}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def create_signed_token(payload: dict[str, Any], secret: str, expires_delta: timedelta) -> str:
    issued_at = utc_now()
    complete_payload = {
        **payload,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + expires_delta).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_segment = _b64url_encode(
        json.dumps(complete_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_signed_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise SecurityError("Invalid token format.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise SecurityError("Invalid token signature.")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SecurityError("Invalid token payload.") from exc

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise SecurityError("Token expiry is missing.")
    if expires_at <= int(utc_now().timestamp()):
        raise SecurityError("Token expired.")
    return payload
