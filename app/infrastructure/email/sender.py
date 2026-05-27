"""Async email sender using aiosmtplib.

When ``smtp_host`` is empty the sender operates in dry-run mode: emails are
logged to stdout/logger instead of being transmitted, which makes development
and testing safe without an SMTP relay.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailSender:
    """Thin wrapper around aiosmtplib that honours the dry-run mode."""

    def __init__(
        self,
        host: str,
        port: int,
        use_tls: bool,
        username: str,
        password: str,
        from_email: str,
        from_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._use_tls = use_tls
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name

    @property
    def is_dry_run(self) -> bool:
        return not self._host

    async def send(
        self,
        to_addresses: list[str],
        subject: str,
        html_body: str,
        text_body: str = "",
    ) -> None:
        """Send an email to one or more addresses.

        Raises ``EmailSendError`` on SMTP failure.
        In dry-run mode (no smtp_host) logs the email and returns.
        """
        if self.is_dry_run:
            logger.info(
                "email_dry_run subject=%r to=%s (set SMTP_HOST to enable real delivery)",
                subject,
                to_addresses,
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = ", ".join(to_addresses)

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        import aiosmtplib

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                start_tls=self._use_tls,
                username=self._username or None,
                password=self._password or None,
            )
            logger.info(
                "email_sent subject=%r to=%s",
                subject,
                to_addresses,
            )
        except Exception as exc:
            raise EmailSendError(str(exc)) from exc


class EmailSendError(RuntimeError):
    pass


def build_sender() -> EmailSender:
    """Create an EmailSender from application settings."""
    from app.core.settings import settings

    return EmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        use_tls=settings.smtp_use_tls,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
    )
