"""Job management endpoints."""
from __future__ import annotations

import uuid
from typing import Any, Iterable, Sequence

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.ui import templates
from app.db import models
from app.db.session import get_session
from app.db.utils import get_default_profile
from app.tasks import jobs as job_tasks
from app.tasks.queue import ingest_all_task

LOGGER = structlog.get_logger(__name__)

router = APIRouter()


class IngestRequest(BaseModel):
    """Payload accepted by the ingest run endpoint."""

    sources: Sequence[str] | None = None
    limit: int | None = None
    dry_run: bool = False


def _wants_html(request: Request) -> bool:
    if request.headers.get("hx-request") == "true":
        return True
    accept = request.headers.get("accept", "")
    return "text/html" in accept or "application/xhtml+xml" in accept


def _serialize_job(job: models.Job, match: models.Match | None) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "source": job.source,
        "url": job.url,
        "location": job.location,
        "remote": job.remote,
        "posted_at": job.posted_at,
        "score": match.score if match is not None else None,
        "reason": match.reason if match is not None else None,
    }


def _serialize_job_detail(job: models.Job, match: models.Match | None) -> dict[str, Any]:
    payload = _serialize_job(job, match)
    payload.update(
        {
            "description_html": job.description_html,
            "description_text": job.description_text,
            "tags": job.tags,
        }
    )
    return payload


def get_job_summaries(
    db: Session,
    *,
    q: str | None = None,
    remote: bool | None = None,
    location: str | None = None,
    min_score: float | None = None,
) -> tuple[list[dict[str, Any]], models.Profile | None]:
    """Return serialized job summaries and the active profile."""

    profile = get_default_profile(db)
    profile_id = profile.id if profile is not None else None
    match_alias = aliased(models.Match)
    join_condition = match_alias.job_id == models.Job.id
    if profile_id is not None:
        join_condition = and_(join_condition, match_alias.profile_id == profile_id)

    stmt = (
        select(models.Job, match_alias)
        .outerjoin(match_alias, join_condition)
        .order_by(models.Job.posted_at.desc().nullslast(), models.Job.created_at.desc())
    )

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                models.Job.title.ilike(like),
                models.Job.company.ilike(like),
                models.Job.description_text.ilike(like),
            )
        )
    if remote is not None:
        stmt = stmt.where(models.Job.remote.is_(remote))
    if location:
        stmt = stmt.where(models.Job.location.ilike(f"%{location}%"))
    if min_score is not None and profile_id is not None:
        stmt = stmt.where(match_alias.score >= float(min_score))

    rows: Iterable[tuple[models.Job, models.Match | None]] = db.execute(stmt).all()
    jobs = [_serialize_job(job, match) for job, match in rows]
    return jobs, profile


@router.get("/jobs")
def list_jobs(
    q: str | None = Query(default=None, description="Search term"),
    remote: bool | None = Query(default=None),
    location: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List jobs stored in the database with optional filters."""

    jobs, _ = get_job_summaries(
        db, q=q, remote=remote, location=location, min_score=min_score
    )
    return jobs


@router.get("/jobs/{job_id}")
def get_job(
    job_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Return detailed job information or render the job detail view."""

    profile = get_default_profile(db)
    profile_id = profile.id if profile is not None else None
    match_alias = aliased(models.Match)
    join_condition = match_alias.job_id == models.Job.id
    if profile_id is not None:
        join_condition = and_(join_condition, match_alias.profile_id == profile_id)

    stmt = (
        select(models.Job, match_alias)
        .outerjoin(match_alias, join_condition)
        .where(models.Job.id == job_id)
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    job, match = row
    payload = _serialize_job_detail(job, match)
    if _wants_html(request):
        return templates.TemplateResponse(  # type: ignore[return-value]
            "job_detail.html",
            {"request": request, "job": payload, "profile": profile},
        )

    return payload


@router.post("/ingest/run")
def trigger_ingest(
    request: Request,
    payload: IngestRequest = Body(default_factory=IngestRequest),
) -> dict[str, Any] | HTMLResponse:
    """Trigger ingestion and matching via Celery with a synchronous fallback."""

    try:
        async_result = ingest_all_task.delay(
            sources=list(payload.sources) if payload.sources is not None else None,
            limit=payload.limit,
            dry_run=payload.dry_run,
        )
        if request.headers.get("hx-request") == "true":
            return HTMLResponse(
                f"Queued ingestion task {async_result.id[:8]}…",
                media_type="text/plain",
            )
        return {"status": "queued", "task_id": async_result.id}
    except Exception as exc:  # pragma: no cover - network/broker failures
        LOGGER.warning("ingest.queue_failed", error=str(exc))

    results = job_tasks.ingest_all(
        sources=list(payload.sources) if payload.sources is not None else None,
        limit=payload.limit,
        dry_run=payload.dry_run,
    )
    matches = 0
    if not payload.dry_run:
        matches = job_tasks.match_default_profile()

    response_payload = {
        "status": "completed",
        "queued": False,
        "ingested": len(results),
        "matches": matches,
        "results": [result.as_dict() for result in results],
    }
    if request.headers.get("hx-request") == "true":
        return HTMLResponse(
            f"Ingested {len(results)} sources — {matches} matches refreshed",
            media_type="text/plain",
        )

    return response_payload


__all__ = ["get_job_summaries"]
