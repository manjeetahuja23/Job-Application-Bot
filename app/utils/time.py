"""Time utility helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from dateutil import tz


def now_utc() -> datetime:
    """Return the current UTC timestamp with timezone info."""

    return datetime.now(timezone.utc)


def convert_timezone(dt: datetime, zone: str) -> datetime:
    """Convert a datetime to the specified timezone."""

    target = tz.gettz(zone)
    if target is None:
        raise ValueError(f"Unknown timezone: {zone}")
    return dt.astimezone(target)
