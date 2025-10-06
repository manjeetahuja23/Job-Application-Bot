"""Celery beat schedule definitions."""
from __future__ import annotations

from datetime import timedelta

from celery.schedules import crontab


def get_beat_schedule() -> dict[str, dict[str, object]]:
    """Return the Celery beat schedule for periodic ingestion and matching."""

    return {
        "ingest-every-three-hours": {
            "task": "app.tasks.queue.ingest_all_task",
            "schedule": timedelta(hours=3),
            "args": [],
        },
        "match-default-profile": {
            "task": "app.tasks.queue.match_default_profile_task",
            "schedule": crontab(minute=5, hour="*/3"),
            "args": [],
        },
    }


__all__ = ["get_beat_schedule"]
