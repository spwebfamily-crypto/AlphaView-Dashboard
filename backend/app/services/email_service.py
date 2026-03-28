from __future__ import annotations

import mimetypes
import logging
import smtplib
import time
from html import escape
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import Settings

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

    def _build_verification_email_bodies(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        code: str,
        ttl_minutes: int,
    ) -> tuple[str, str]:
        greeting_name = escape(recipient_name or recipient_email)
        safe_code = escape(code)
        dashboard_url = self.settings.frontend_base_url.rstrip("/") or "http://localhost:5173"
        preheader = f"Your AlphaView confirmation code is {code}. It expires in {ttl_minutes} minutes."

        text_body = (
            f"Hello {recipient_name or recipient_email},\n\n"
            "Welcome to AlphaView.\n\n"
            "Use the confirmation code below to verify your email address:\n\n"
            f"{code}\n\n"
            f"This code expires in {ttl_minutes} minutes.\n\n"
            f"Open AlphaView: {dashboard_url}\n\n"
            "If you did not create this account, you can ignore this email.\n"
        )

        html_body = f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AlphaView Confirmation Code</title>
  </head>
  <body style="margin:0; padding:0; background-color:#070b14; color:#e5e7eb; font-family:'Segoe UI',Arial,sans-serif;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all;">{escape(preheader)}</div>
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#070b14; margin:0; padding:0;">
      <tr>
        <td align="center" style="padding:28px 14px;">
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:660px; background:#0b1220; border:1px solid #182233; border-radius:26px; overflow:hidden;">
            <tr>
              <td style="padding:0;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:linear-gradient(135deg,#070b14 0%,#0f172a 48%,#151f38 100%);">
                  <tr>
                    <td align="center" style="padding:30px 24px 10px 24px;">
                      <img src="cid:{{{{LOGO_CID}}}}" alt="AlphaView SMTP System" width="320" style="display:block; width:100%; max-width:320px; height:auto; margin:0 auto 14px auto;" />
                      <div style="font-size:26px; line-height:1.2; font-weight:800; color:#ffffff;">AlphaView secure email verification</div>
                      <div style="margin-top:8px; font-size:15px; line-height:1.7; color:#cbd5e1;">
                        Research-grade access for your equities dashboard starts here.
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:0 24px 26px 24px;">
                      <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:linear-gradient(180deg,#0f172a 0%,#111827 100%); border:1px solid #253247; border-radius:22px;">
                        <tr>
                          <td style="padding:26px 24px;">
                            <div style="font-size:13px; line-height:1.7; text-transform:uppercase; letter-spacing:1.6px; color:#94a3b8;">Verification Code</div>
                            <div style="margin-top:12px; font-size:44px; line-height:1; font-weight:800; letter-spacing:10px; color:#ffffff;">{safe_code}</div>
                            <div style="margin-top:14px; font-size:15px; line-height:1.7; color:#cbd5e1;">
                              This code expires in <strong style="color:#ffffff;">{ttl_minutes} minutes</strong>.
                            </div>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 10px 28px; background:#ffffff;">
                <div style="font-size:16px; line-height:1.8; color:#0f172a;">
                  Hello <strong>{greeting_name}</strong>,
                </div>
                <div style="margin-top:12px; font-size:16px; line-height:1.8; color:#334155;">
                  Use the code above to confirm your email address and finish setting up your AlphaView workspace.
                  The platform remains focused on US equities research and paper-trading workflows, with live trading disabled by default.
                </div>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:22px;">
                  <tr>
                    <td align="center" bgcolor="#d61f28" style="border-radius:999px;">
                      <a href="{escape(dashboard_url)}" style="display:inline-block; padding:14px 22px; font-size:14px; line-height:1; font-weight:700; color:#ffffff; text-decoration:none;">
                        Open AlphaView
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px 28px; background:#ffffff;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-collapse:separate; border-spacing:0; background:#f8fafc; border:1px solid #e2e8f0; border-radius:18px;">
                  <tr>
                    <td style="padding:18px 20px;">
                      <div style="font-size:12px; line-height:1.7; text-transform:uppercase; letter-spacing:1.4px; color:#64748b;">Security Note</div>
                      <div style="margin-top:8px; font-size:14px; line-height:1.8; color:#475569;">
                        If you did not create this account, you can safely ignore this email. No changes will be made unless the code is used.
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 28px 28px 28px; background:#0b1220; border-top:1px solid #182233;">
                <div style="font-size:12px; line-height:1.8; color:#94a3b8;">
                  AlphaView SMTP System<br />
                  Institutional-style communication for the AlphaView research and paper-trading platform.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
        return text_body, html_body

    def send_verification_code(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        code: str,
        ttl_minutes: int,
    ) -> None:
        text_body, html_body = self._build_verification_email_bodies(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            code=code,
            ttl_minutes=ttl_minutes,
        )
        self.send_email(
            recipient_email=recipient_email,
            subject="AlphaView confirmation code",
            text_body=text_body,
            html_body=html_body,
        )
