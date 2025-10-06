"""Workday public feed ingestion."""
from __future__ import annotations

from typing import Iterable, Mapping
from urllib.parse import urlparse

from app.ingestion.base import IngestionSource
from app.utils.http import HttpClient


class WorkdayIngestion(IngestionSource):
    """Retrieve job postings from Workday's public search API."""

    source = "workday"

    def __init__(self, search_url: str, client: HttpClient | None = None) -> None:
        super().__init__(client=client)
        self.search_url = search_url
        parsed = urlparse(search_url)
        path_segments = [segment for segment in parsed.path.split("/") if segment]
        self.company = path_segments[2] if len(path_segments) > 2 else parsed.hostname or "Workday"

    def _is_public(self) -> bool:
        parsed = urlparse(self.search_url)
        path = parsed.path.lower()
        return "/wday/" in path and "/cxs/" in path and path.endswith("/jobs")

    def fetch(self, *, limit: int | None = None) -> Iterable[Mapping[str, object]]:
        """Yield normalized Workday postings, if a public endpoint is available."""

        if not self._is_public():
            return []

        response = self.client.get(self.search_url)
        payload = response.json()
        jobs = payload.get("jobPostings", []) if isinstance(payload, dict) else []

        normalised: list[Mapping[str, object]] = []
        for job in jobs:
            posting = job.get("jobPostingInfo", {}) if isinstance(job, dict) else {}
            tags = job.get("keywords", []) or posting.get("keywords", []) or []
            normalised.append(
                {
                    "source": self.source,
                    "external_id": job.get("jobPostingId", ""),
                    "url": posting.get("externalUrl") or posting.get("careerPageUrl") or "",
                    "company": posting.get("companyName") or self.company,
                    "title": posting.get("title") or job.get("title", ""),
                    "location": posting.get("location") or job.get("locationsText", ""),
                    "remote": "remote" in str(job.get("locationsText", "")).lower(),
                    "posted_at": posting.get("postedOn") or job.get("postedOn"),
                    "description_html": posting.get("jobDescription", ""),
                    "tags": tags,
                    "raw_json": job,
                }
            )
            if limit is not None and len(normalised) >= limit:
                break
        return normalised
