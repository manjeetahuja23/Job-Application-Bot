"""Configuration utilities for the application."""
from __future__ import annotations

from app.core.settings import AppSettings


def get_settings() -> AppSettings:
    """Return cached settings instance."""

    return AppSettings.from_env()
