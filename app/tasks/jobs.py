"""Background job definitions for ingestion and matching."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.db import models
from app.db.session import session_scope
from app.db.utils import get_default_profile
from app.ingestion.base import IngestionSource, IngestResult, upsert_job
from app.ingestion.greenhouse import GreenhouseIngestion
from app.ingestion.lever import LeverIngestion
from app.ingestion.workday_public import WorkdayIngestion
from app.matching.filters import (
    filter_by_geo,
    filter_by_min_score,
    filter_by_title_keywords,
)
from app.matching.scorer import score
from app.matching.vectorizer import TextVectorizer
from app.notify.emailer import send_match_digest
from app.notify.telegram import send_message

LOGGER = structlog.get_logger(__name__)


def _load_seed_sources() -> dict[str, list[Mapping[str, object] | str]]:
    """Load configured ingestion sources from the seed file."""

    candidate_paths = [
        Path(__file__).resolve().parents[2] / "seed_companies.json",
        Path(__file__).with_name("seed_companies.json"),
    ]
    data: object | None = None
    for path in candidate_paths:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            break
    if data is None:
        LOGGER.info("seed.sources.missing")
        return {}
    result: dict[str, list[Mapping[str, object] | str]] = {}
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, Mapping):
                source = str(entry.get("source", "")).lower()
                if not source:
                    continue
                result.setdefault(source, []).append(dict(entry))
    elif isinstance(data, Mapping):
        for key, value in data.items():
            if isinstance(value, list):
                cleaned = [item for item in value if isinstance(item, str | Mapping)]
                result[str(key)] = [
                    dict(item) if isinstance(item, Mapping) else item
                    for item in cleaned
                ]
    return result


def _build_ingestor(source: str, entry: Mapping[str, object] | str) -> IngestionSource:
    """Create an ingestion source instance from configuration."""

    if source == "greenhouse":
        board = entry if isinstance(entry, str) else entry.get("board", "")
        if not board:
            raise ValueError("Greenhouse configuration requires a board URL")
        return GreenhouseIngestion(board_url=str(board))
    if source == "lever":
        company = entry if isinstance(entry, str) else entry.get("company", "")
        if not company:
            raise ValueError("Lever configuration requires a company handle")
        return LeverIngestion(company=str(company))
    if source == "workday":
        search_url = entry if isinstance(entry, str) else entry.get("url", "")
        if not search_url:
            raise ValueError("Workday configuration requires a search URL")
        return WorkdayIngestion(search_url=str(search_url))
    raise ValueError(f"Unsupported ingestion source: {source}")


def ingest_all(
    sources: Sequence[str] | None = None,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> list[IngestResult]:
    """Run ingestion for all configured sources and return summary results."""

    configured_sources = _load_seed_sources()
    targets = list(sources) if sources else list(configured_sources.keys())
    results: list[IngestResult] = []

    with session_scope() as session:
        for source in targets:
            entries = configured_sources.get(source, [])
            for entry in entries:
                ingestor = _build_ingestor(source, entry)
                LOGGER.info(
                    "ingest.start",
                    source=ingestor.source,
                    target=str(entry),
                    limit=limit,
                    dry_run=dry_run,
                )
                result = ingestor.ingest(session, limit=limit, dry_run=dry_run)
                LOGGER.info("ingest.complete", **result.as_dict())
                results.append(result)
    return results


def match_all(profile_id: int, min_score: float | None = None) -> int:
    """Generate match records for the given profile based on scoring and filters."""

    settings = get_settings()
    threshold = float(min_score if min_score is not None else settings.min_score)

    with session_scope() as session:
        profile = session.get(models.Profile, profile_id)
        if profile is None:
            raise ValueError(f"Profile {profile_id} not found")

        jobs = list(session.execute(select(models.Job)).scalars())
        if not jobs:
            return 0

        vectorizer = TextVectorizer()
        descriptions = [job.description_text for job in jobs]
        vectorizer.fit_jobs(descriptions)
        profile_vector = vectorizer.transform_profile(profile.skills)

        keyword_candidates = [
            keyword.strip()
            for keyword in (profile.keywords or "").split(",")
            if keyword.strip()
        ]
        if not keyword_candidates:
            keyword_candidates = settings.match_keywords

        job_candidates: list[dict[str, object]] = []
        for index, job in enumerate(jobs):
            job_vector = vectorizer.job_vector(index)
            result = score(
                job.description_text,
                profile.skills,
                keyword_candidates,
                job_vector=job_vector,
                profile_vector=profile_vector,
            )
            job_candidates.append(
                {
                    "job": job,
                    "score": result.score,
                    "matched_keywords": result.matched_keywords,
                    "cosine": result.cosine_similarity,
                    "location": job.location or "",
                    "remote": job.remote,
                    "title": job.title,
                },
            )

        geo_filtered = filter_by_geo(job_candidates, settings.geo_filter_keywords)
        score_filtered = filter_by_min_score(geo_filtered, threshold)
        title_filtered = filter_by_title_keywords(
            score_filtered,
            settings.title_keywords,
        )
        title_filtered.sort(key=lambda item: float(item["score"]), reverse=True)

        matches_written = 0
        for item in title_filtered:
            job = item["job"]
            reason_keywords = list(item.get("matched_keywords", []))
            if reason_keywords:
                reason = "Matched keywords: " + ", ".join(reason_keywords[:5])
            else:
                reason = f"Cosine similarity {float(item.get('cosine', 0.0)):.2f}"

            existing = (
                session.query(models.Match)
                .filter_by(job_id=job.id, profile_id=profile.id)
                .one_or_none()
            )
            if existing:
                existing.score = float(item["score"])
                existing.reason = reason
                LOGGER.info(
                    "match.update",
                    job_id=str(job.id),
                    profile_id=profile.id,
                    score=existing.score,
                )
            else:
                match = models.Match(
                    job_id=job.id,
                    profile_id=profile.id,
                    score=float(item["score"]),
                    reason=reason,
                )
                session.add(match)
                LOGGER.info(
                    "match.create",
                    job_id=str(job.id),
                    profile_id=profile.id,
                    score=match.score,
                )
            matches_written += 1

        return matches_written


def match_default_profile(min_score: float | None = None) -> int:
    """Match jobs against the default profile when available."""

    with session_scope() as session:
        profile = get_default_profile(session)
        if profile is None:
            LOGGER.warning("match.default_profile_missing")
            return 0

        profile_id = profile.id

    return match_all(profile_id, min_score=min_score)


def email_digest(profile_id: int | None = None, limit: int = 10) -> int:
    """Send a digest of recent matches via email (and Telegram when configured)."""

    settings = get_settings()
    profile_name = "Default Profile"
    target_profile_id: int | None = None
    with session_scope() as session:
        target_profile = None
        if profile_id is not None:
            target_profile = session.get(models.Profile, profile_id)
        if target_profile is None:
            target_profile = get_default_profile(session)
        if target_profile is None:
            LOGGER.warning("notify.digest.profile_missing")
            return 0
        profile_name = target_profile.name or profile_name
        target_profile_id = target_profile.id

        stmt = (
            select(models.Match, models.Job)
            .join(models.Job, models.Match.job_id == models.Job.id)
            .where(models.Match.profile_id == target_profile.id)
            .order_by(models.Match.created_at.desc())
            .limit(limit)
        )
        rows = session.execute(stmt).all()

        matches_payload: list[dict[str, str]] = []
        for match, job in rows:
            matches_payload.append(
                {
                    "title": job.title or "",
                    "company": job.company or "",
                    "score": f"{match.score:.2f}",
                    "url": job.url or "",
                },
            )

    if not matches_payload or target_profile_id is None:
        LOGGER.info("notify.digest.no_matches", profile=profile_name)
        return 0

    send_match_digest(
        profile_name,
        matches_payload,
        to_address=settings.email_from,
    )

    telegram_lines = [
        f"{item['title']} @ {item['company']} ({item['score']})\n{item['url']}"
        for item in matches_payload[:5]
        if item.get("title")
    ]
    if telegram_lines:
        send_message(
            "Recent matches for {name}:\n{body}".format(
                name=profile_name,
                body="\n\n".join(telegram_lines),
            ),
        )

    LOGGER.info(
        "notify.digest.sent",
        profile_id=target_profile_id,
        matches=len(matches_payload),
    )
    return len(matches_payload)


def bootstrap_defaults() -> None:
    """Load a simple default job entry for smoke testing."""

    payload = {
        "source": "bootstrap",
        "external_id": "default-job",
        "url": "https://example.com/jobs/default",
        "company": "Example Corp",
        "title": "Automation Engineer",
        "location": "Remote",
        "remote": True,
        "description_html": "<p>Builds automation workflows.</p>",
        "description_text": "Builds automation workflows.",
    }
    with session_scope() as session:
        upsert_job(session, payload)
