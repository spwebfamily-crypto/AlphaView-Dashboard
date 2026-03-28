from __future__ import annotations

import mimetypes
import logging
import smtplib
import time
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import httpx

from app.core.config import EmailDeliveryMode, Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SmtpEmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.email_smtp_host and self.settings.email_from_email)

    def _logo_asset_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets" / "alphaview-email-logo.svg"

    def _load_logo_asset(self) -> tuple[bytes, str] | None:
        asset_path = self._logo_asset_path()
        if not asset_path.exists():
            return None

        mime_type, _ = mimetypes.guess_type(asset_path.name)
        if not mime_type:
            return None

        return asset_path.read_bytes(), mime_type

    def _build_email_message(
        self,
        *,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["To"] = recipient_email
        message["From"] = formataddr((self.settings.email_from_name, self.settings.email_from_email or ""))
        message["Subject"] = subject
        message.set_content(text_body)

        if not html_body:
            return message

        logo_cid = make_msgid(domain="alphaview.local")
        html_with_logo = html_body.replace("{{LOGO_CID}}", logo_cid[1:-1])
        message.add_alternative(html_with_logo, subtype="html")

        logo_payload = self._load_logo_asset()
        html_part = message.get_body(preferencelist=("html",))
        if logo_payload and html_part is not None:
            logo_bytes, mime_type = logo_payload
            maintype, subtype = mime_type.split("/", 1)
            html_part.add_related(
                logo_bytes,
                maintype=maintype,
                subtype=subtype,
                cid=logo_cid,
                filename=self._logo_asset_path().name,
            )

        return message

    def send_email(
        self,
        *,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        if self.settings.email_delivery_mode == EmailDeliveryMode.LOG:
            logger.info(
                "email_delivery_logged",
                extra={
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "text_body": text_body,
                },
            )
            return

        if self.settings.email_delivery_mode == EmailDeliveryMode.RESEND:
            self._send_via_resend(
                recipient_email=recipient_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
            return

        if not self.enabled:
            raise EmailDeliveryError(
                "Email delivery is not configured. Set Gmail-compatible SMTP credentials first.",
                status_code=503,
            )

        message = self._build_email_message(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        retries = 3
        for attempt in range(retries):
            try:
                if self.settings.email_smtp_use_ssl:
                    smtp_client = smtplib.SMTP_SSL(
                        self.settings.email_smtp_host,
                        self.settings.email_smtp_port,
                        timeout=self.settings.request_timeout_seconds,
                    )
                else:
                    smtp_client = smtplib.SMTP(
                        self.settings.email_smtp_host,
                        self.settings.email_smtp_port,
                        timeout=self.settings.request_timeout_seconds,
                    )

                with smtp_client as client:
                    client.ehlo()
                    if self.settings.email_smtp_use_starttls and not self.settings.email_smtp_use_ssl:
                        client.starttls()
                        client.ehlo()
                    if self.settings.email_smtp_username:
                        client.login(
                            self.settings.email_smtp_username,
                            self.settings.email_smtp_password or "",
                        )
                    client.send_message(message)
                    return
            except (OSError, smtplib.SMTPException) as exc:
                logger.warning("email_delivery_attempt_failed", extra={"attempt": attempt + 1, "error": str(exc)})
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise EmailDeliveryError("Email delivery failed after retries.", status_code=502) from exc

    def _send_via_resend(
        self,
        *,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        if not self.settings.resend_api_key or not self.settings.email_from_email:
            raise EmailDeliveryError(
                "Resend delivery is not configured. Set RESEND_API_KEY and EMAIL_FROM_EMAIL first.",
                status_code=503,
            )

        payload = {
            "from": formataddr((self.settings.email_from_name, self.settings.email_from_email)),
            "to": [recipient_email],
            "subject": subject,
            "text": text_body,
        }
        if html_body:
            payload["html"] = html_body

        retries = 3
        for attempt in range(retries):
            try:
                response = httpx.post(
                    f"{self.settings.resend_api_base.rstrip('/')}/emails",
                    headers={
                        "Authorization": f"Bearer {self.settings.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.settings.request_timeout_seconds,
                )
                if response.is_success:
                    response_payload = response.json()
                    logger.info(
                        "email_delivery_sent",
                        extra={
                            "provider": "resend",
                            "recipient_email": recipient_email,
                            "email_id": response_payload.get("id"),
                        },
                    )
                    return

                error_detail = "Resend email delivery failed."
                try:
                    response_payload = response.json()
                    if isinstance(response_payload, dict):
                        error_detail = (
                            response_payload.get("message")
                            or response_payload.get("error")
                            or error_detail
                        )
                except ValueError:
                    if response.text:
                        error_detail = response.text

                logger.warning(
                    "email_delivery_attempt_failed",
                    extra={
                        "provider": "resend",
                        "attempt": attempt + 1,
                        "status_code": response.status_code,
                        "error": error_detail,
                    },
                )
                if response.status_code >= 500 and attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise EmailDeliveryError(error_detail, status_code=502)
            except httpx.RequestError as exc:
                logger.warning(
                    "email_delivery_attempt_failed",
                    extra={"provider": "resend", "attempt": attempt + 1, "error": str(exc)},
                )
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise EmailDeliveryError("Resend email delivery failed after retries.", status_code=502) from exc
