"""Celery application wiring for background jobs."""
from __future__ import annotations

from typing import Any, Sequence

import structlog
from celery import Celery

from app.core.config import get_settings
from app.tasks import jobs
from app.tasks.schedules import get_beat_schedule

LOGGER = structlog.get_logger(__name__)


def _create_celery() -> Celery:
    """Instantiate the Celery app with configuration from settings."""

    settings = get_settings()
    app = Celery("autojob_bot")
    app.conf.broker_url = settings.redis_url
    app.conf.result_backend = settings.redis_url
    app.conf.task_default_queue = "default"
    app.conf.timezone = settings.timezone
    app.conf.enable_utc = True
    app.conf.task_always_eager = settings.celery_eager
    app.conf.task_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.result_serializer = "json"
    app.conf.beat_schedule = get_beat_schedule()
    return app


celery_app = _create_celery()


@celery_app.task(name="app.tasks.queue.ingest_all_task")
def ingest_all_task(
    sources: Sequence[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Celery task that runs all configured ingestors."""

    results = jobs.ingest_all(sources=sources, limit=limit, dry_run=dry_run)
    LOGGER.info("tasks.ingest_all.completed", count=len(results))
    try:
        match_default_profile_task.delay()
    except Exception as exc:  # pragma: no cover - best effort queueing
        LOGGER.warning("tasks.match.queue_failed", error=str(exc))
    return [result.as_dict() for result in results]


@celery_app.task(name="app.tasks.queue.match_default_profile_task")
def match_default_profile_task(min_score: float | None = None) -> int:
    """Celery task that runs matching for the default profile."""

    matches = jobs.match_default_profile(min_score=min_score)
    LOGGER.info("tasks.match.completed", matches=matches)
    return matches


__all__ = ["celery_app", "ingest_all_task", "match_default_profile_task"]
