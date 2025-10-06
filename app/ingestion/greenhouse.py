"""Greenhouse ingestion implementation."""
from __future__ import annotations

from typing import Iterable, Mapping
from urllib.parse import urlparse

import httpx

from app.ingestion.base import IngestionSource
from app.utils.http import HttpClient


class GreenhouseIngestion(IngestionSource):
    """Retrieve job postings from the Greenhouse public API."""

    source = "greenhouse"

    def __init__(self, board_url: str, client: HttpClient | None = None) -> None:
        super().__init__(client=client)
        self.board_url = board_url.rstrip("/")
        self._etag: str | None = None
        parsed = urlparse(self.board_url)
        path_segments = [segment for segment in parsed.path.split("/") if segment]
        self.company = path_segments[-1] if path_segments else parsed.hostname or "Greenhouse"

    def _jobs_url(self) -> str:
        if self.board_url.endswith("/jobs"):
            base = self.board_url
        else:
            base = f"{self.board_url}/jobs"
        return f"{base}?content=true"

    def fetch(self, *, limit: int | None = None) -> Iterable[Mapping[str, object]]:
        """Yield normalized Greenhouse postings."""

        headers = {"If-None-Match": self._etag} if self._etag else None
        response = self.client.get(self._jobs_url(), headers=headers)
        if response.status_code == httpx.codes.NOT_MODIFIED:
            return []
        if etag := response.headers.get("ETag"):
            self._etag = etag
        payload = response.json()
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

        normalised: list[Mapping[str, object]] = []
        for job in jobs:
            html = job.get("content", "")
            location = job.get("location", {}) or {}
            metadata = job.get("metadata", []) or []
            departments = job.get("departments", []) or []
            offices = job.get("offices", []) or []
            tags: list[str] = []
            tags.extend([item.get("name", "") for item in departments if isinstance(item, dict)])
            tags.extend([item.get("name", "") for item in offices if isinstance(item, dict)])
            tags.extend([item.get("value", "") for item in metadata if isinstance(item, dict)])

            normalised.append(
                {
                    "source": self.source,
                    "external_id": str(job.get("id", "")),
                    "url": job.get("absolute_url")
                    or f"{self.board_url}/jobs/{job.get('id')}",
                    "company": self.company,
                    "title": job.get("title", ""),
                    "location": location.get("name", ""),
                    "remote": "remote" in str(location.get("name", "")).lower(),
                    "posted_at": job.get("updated_at") or job.get("created_at"),
                    "description_html": html,
                    "tags": tags,
                    "raw_json": job,
                }
            )
            if limit is not None and len(normalised) >= limit:
                break
        return normalised
