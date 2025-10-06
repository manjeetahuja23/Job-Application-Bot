"""Base ingestion interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from dateutil import parser as date_parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.parsing.clean_html import clean_html
from app.parsing.extract_salary import extract_salary_range
from app.parsing.normalize_location import LocationDetails, normalize_location
from app.utils.http import HttpClient


@dataclass
class IngestResult:
    """Summary of an ingestion run."""

    source: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int | str]:
        """Return the ingestion result as a serialisable dictionary."""

        return {
            "source": self.source,
            "fetched": self.fetched,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
        }


class IngestionSource(ABC):
    """Abstract base class for job ingestion sources."""

    source: str

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    @abstractmethod
    def fetch(self, *, limit: int | None = None) -> Iterable[Mapping[str, Any]]:
        """Yield raw job payloads from the source."""

    def ingest(
        self,
        session: Session,
        *,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> IngestResult:
        """Fetch jobs and upsert them into the database."""

        result = IngestResult(source=self.source)
        for payload in self.fetch(limit=limit):
            result.fetched += 1
            if dry_run:
                result.skipped += 1
                continue
            _, status = upsert_job(session, payload)
            if status == "inserted":
                result.inserted += 1
            elif status == "updated":
                result.updated += 1
            else:
                result.skipped += 1
        if not dry_run:
            session.flush()
        return result


def _coerce_datetime(value: Any) -> datetime | None:
    """Parse arbitrary date inputs into an aware UTC datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = date_parser.parse(str(value))
        except (ValueError, TypeError, OverflowError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize job payload keys to a consistent structure."""

    source = str(payload.get("source", "unknown"))
    html_description = str(payload.get("description_html") or payload.get("description") or "")
    text_description = payload.get("description_text") or clean_html(html_description)
    location_info: LocationDetails = normalize_location(str(payload.get("location", "")))
    salary_text = payload.get("salary_text") or f"{html_description}\n{text_description}"
    salary_range = payload.get("salary_range") or extract_salary_range(str(salary_text))

    tags = payload.get("tags", [])
    if isinstance(tags, str):
        tag_list = [part.strip() for part in tags.split(",") if part.strip()]
    else:
        tag_list = [str(part).strip() for part in tags if str(part).strip()]

    posted_at = _coerce_datetime(payload.get("posted_at"))

    normalized = {
        "source": source,
        "external_id": str(payload.get("external_id", "")),
        "url": str(payload.get("url", "")),
        "company": str(payload.get("company", "")) or "Unknown",
        "title": str(payload.get("title", "")),
        "location": location_info.normalized,
        "remote": bool(payload.get("remote", location_info.is_remote)),
        "posted_at": posted_at,
        "description_html": html_description,
        "description_text": str(text_description),
        "tags": ",".join(tag_list),
        "salary_min": salary_range[0] if salary_range else None,
        "salary_max": salary_range[1] if salary_range else None,
        "raw_json": payload.get("raw_json") or payload.get("raw") or dict(payload),
    }

    return normalized


def upsert_job(session: Session, payload: Mapping[str, Any]) -> tuple[Job, str]:
    """Insert or update a job record from a normalized payload."""

    normalized = normalize_payload(payload)
    stmt = select(Job).where(
        Job.source == normalized["source"],
        Job.external_id == normalized["external_id"],
    )
    existing = session.execute(stmt).scalar_one_or_none()

    updatable_fields = {
        "url",
        "company",
        "title",
        "location",
        "remote",
        "posted_at",
        "description_html",
        "description_text",
        "tags",
        "salary_min",
        "salary_max",
        "raw_json",
    }

    if existing is None:
        job = Job(**normalized)
        session.add(job)
        return job, "inserted"

    changed = False
    for field in updatable_fields:
        new_value = normalized[field]
        if getattr(existing, field) != new_value:
            setattr(existing, field, new_value)
            changed = True
    if changed:
        session.add(existing)
        return existing, "updated"
    return existing, "unchanged"
