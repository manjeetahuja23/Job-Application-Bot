"""Lever ingestion implementation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping

from app.ingestion.base import IngestionSource
from app.utils.http import HttpClient


class LeverIngestion(IngestionSource):
    """Retrieve job postings from the Lever API."""

    source = "lever"

    def __init__(self, company: str, client: HttpClient | None = None) -> None:
        super().__init__(client=client)
        self.company = company

    def fetch(self, *, limit: int | None = None) -> Iterable[Mapping[str, object]]:
        """Yield normalized Lever postings."""

        url = f"https://api.lever.co/v0/postings/{self.company}?mode=json"
        response = self.client.get(url)
        data = response.json()
        jobs = data if isinstance(data, list) else []

        normalised: list[Mapping[str, object]] = []
        for job in jobs:
            created_at = job.get("createdAt")
            posted_at: datetime | int | float | None = None
            if isinstance(created_at, (int, float)):
                posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
            else:
                posted_at = created_at

            normalised.append(
                {
                    "source": self.source,
                    "external_id": job.get("id", ""),
                    "url": job.get("hostedUrl") or job.get("applyUrl") or "",
                    "company": job.get("categories", {}).get("team", self.company),
                    "title": job.get("text", ""),
                    "location": job.get("categories", {}).get("location", ""),
                    "remote": job.get("workplaceType", "").lower() == "remote",
                    "posted_at": posted_at,
                    "description_html": job.get("description", ""),
                    "tags": job.get("tags", []),
                    "salary_text": job.get("salary", ""),
                    "raw_json": job,
                }
            )
            if limit is not None and len(normalised) >= limit:
                break
        return normalised
