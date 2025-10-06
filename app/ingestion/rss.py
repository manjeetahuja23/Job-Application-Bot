"""RSS feed ingestion."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable, Mapping

import feedparser

from app.ingestion.base import IngestionSource
from app.utils.http import HttpClient


class RSSIngestion(IngestionSource):
    """Retrieve job postings from a generic RSS or Atom feed."""

    source = "rss"

    def __init__(self, feed_url: str, client: HttpClient | None = None) -> None:
        super().__init__(client=client)
        self.feed_url = feed_url

    def fetch(self, *, limit: int | None = None) -> Iterable[Mapping[str, object]]:
        """Yield normalized entries from the RSS feed."""

        text = self.client.get_text(self.feed_url)
        parsed = feedparser.parse(text)
        entries = parsed.get("entries", [])

        normalised: list[Mapping[str, object]] = []
        for entry in entries:
            guid = entry.get("id") or entry.get("guid") or entry.get("link", "")
            if guid:
                external_id = hashlib.sha256(guid.encode("utf-8")).hexdigest()
            else:
                external_id = hashlib.sha256(entry.get("title", "").encode("utf-8")).hexdigest()

            published = entry.get("published_parsed")
            posted_at: datetime | None = None
            if published:
                posted_at = datetime(*published[:6], tzinfo=timezone.utc)

            summary = entry.get("summary", "")
            tags = [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")]

            normalised.append(
                {
                    "source": self.source,
                    "external_id": external_id,
                    "url": entry.get("link", ""),
                    "company": entry.get("author", ""),
                    "title": entry.get("title", ""),
                    "location": entry.get("location", ""),
                    "remote": "remote" in str(entry.get("location", "")).lower(),
                    "posted_at": posted_at,
                    "description_html": summary,
                    "tags": tags,
                    "raw_json": entry,
                }
            )
            if limit is not None and len(normalised) >= limit:
                break
        return normalised
