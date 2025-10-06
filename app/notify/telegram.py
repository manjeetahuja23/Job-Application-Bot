"""Telegram notification helpers."""
from __future__ import annotations

import httpx
import structlog

from app.core.config import get_settings

LOGGER = structlog.get_logger(__name__)


def send_message(text: str) -> None:
    """Send a message to the configured Telegram chat."""

    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        LOGGER.info("notify.telegram.skipping")
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.telegram_chat_id, "text": text}
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        LOGGER.warning("notify.telegram.failed", error=str(exc))


__all__ = ["send_message"]
