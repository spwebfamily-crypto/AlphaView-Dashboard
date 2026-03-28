from __future__ import annotations

from app.core.config import Settings
from app.services.email_service import SmtpEmailService


def test_verification_email_message_includes_html_and_inline_logo() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        email_smtp_host="smtp.gmail.com",
        email_smtp_port=465,
        email_smtp_use_ssl=True,
        email_smtp_username="mailer@example.com",
        email_smtp_password="app-password",
        email_from_email="mailer@example.com",
        email_from_name="AlphaView SMTP System",
        frontend_base_url="https://alphaview.example.com",
    )
    service = SmtpEmailService(settings)
    text_body, html_body = service._build_verification_email_bodies(
        recipient_email="user@example.com",
        recipient_name="Trader Test",
        code="246810",
        ttl_minutes=10,
    )

    message = service._build_email_message(
        recipient_email="user@example.com",
        subject="AlphaView confirmation code",
        text_body=text_body,
        html_body=html_body,
    )

    plain_part = message.get_body(preferencelist=("plain",))
    html_part = message.get_body(preferencelist=("html",))

    assert plain_part is not None
    assert html_part is not None
    assert "246810" in plain_part.get_content()
    html_content = html_part.get_content()
    assert "AlphaView secure email verification" in html_content
    assert "Open AlphaView" in html_content
    assert "cid:" in html_content
    assert "{{LOGO_CID}}" not in html_content

    related_parts = [part for part in message.walk() if part.get_content_maintype() == "image"]
    assert related_parts
    assert related_parts[0].get_content_type() == "image/svg+xml"
