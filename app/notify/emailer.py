"""Email notification helpers."""
from __future__ import annotations

import smtplib
from collections.abc import Iterable, Sequence
from contextlib import suppress
from email.message import EmailMessage
from smtplib import SMTPException

import structlog

from app.core.config import get_settings

LOGGER = structlog.get_logger(__name__)


def _smtp_configured() -> bool:
    """Return whether SMTP settings are configured enough to send mail."""

    settings = get_settings()
    if not settings.email_smtp_host:
        LOGGER.info("notify.email.smtp_missing_host")
        return False
    if not settings.email_from:
        LOGGER.info("notify.email.missing_from")
        return False
    return True


def _build_digest_body(profile_name: str, matches: Sequence[dict[str, str]]) -> str:
    """Create a plain-text digest body for recent matches."""

    lines = [f"Recent matches for {profile_name}", ""]
    for item in matches:
        lines.append(
            "- {title} at {company} (score {score})\n  {url}".format(
                title=item.get("title", "Unknown Role"),
                company=item.get("company", "Unknown Company"),
                score=item.get("score", "0.00"),
                url=item.get("url", ""),
            ),
        )
    lines.append("")
    lines.append("Powered by autojob-bot")
    return "\n".join(lines)


def send_match_digest(
    profile_name: str,
    matches: Iterable[dict[str, str]],
    *,
    to_address: str | None = None,
    subject: str | None = None,
) -> None:
    """Send a match digest email containing the provided matches."""

    matches_list = list(matches)[:10]
    if not matches_list:
        LOGGER.info("notify.email.no_matches")
        return

    if not _smtp_configured():
        LOGGER.info("notify.email.skipping")
        return

    settings = get_settings()
    recipient = to_address or settings.email_from
    if not recipient:
        LOGGER.info("notify.email.missing_recipient")
        return

    email_subject = subject or f"autojob-bot digest for {profile_name}"
    body = _build_digest_body(profile_name, matches_list)

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = email_subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.email_smtp_host) as smtp:
            if settings.email_smtp_user and settings.email_smtp_pass:
                with suppress(SMTPException):
                    smtp.starttls()
                smtp.login(settings.email_smtp_user, settings.email_smtp_pass)
            smtp.send_message(message)
    except (OSError, SMTPException) as exc:  # pragma: no cover
        LOGGER.warning("notify.email.failed", error=str(exc))


__all__ = ["send_match_digest"]
