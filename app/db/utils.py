"""Database utility helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models


def get_default_profile(session: Session) -> models.Profile | None:
    """Return the default profile or the first available profile."""

    settings = get_settings()
    if settings.default_profile_name:
        profile = session.execute(
            select(models.Profile).where(models.Profile.name == settings.default_profile_name)
        ).scalar_one_or_none()
        if profile is not None:
            return profile

    return session.execute(select(models.Profile).order_by(models.Profile.id)).scalar_one_or_none()


__all__ = ["get_default_profile"]
