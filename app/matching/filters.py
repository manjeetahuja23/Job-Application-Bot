"""Filtering helpers for matched jobs."""
from __future__ import annotations

from typing import Iterable, List, Mapping


def _normalize(values: Iterable[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def filter_by_geo(
    jobs: Iterable[Mapping[str, object]],
    allowed_regions: Iterable[str],
) -> List[Mapping[str, object]]:
    """Return jobs that satisfy geo requirements (remote or allowed regions)."""

    allowed = [region.lower() for region in _normalize(allowed_regions)]
    result: list[Mapping[str, object]] = []
    for job in jobs:
        if bool(job.get("remote")):
            result.append(job)
            continue
        location = str(job.get("location", "")).lower()
        if any(marker in location for marker in allowed):
            result.append(job)
    return result


def filter_by_min_score(
    jobs: Iterable[Mapping[str, object]],
    minimum: float,
) -> List[Mapping[str, object]]:
    """Return jobs whose score meets the configured threshold."""

    return [job for job in jobs if float(job.get("score", 0.0)) >= float(minimum)]


def filter_by_title_keywords(
    jobs: Iterable[Mapping[str, object]],
    keywords: Iterable[str],
) -> List[Mapping[str, object]]:
    """Return jobs whose title contains at least one configured keyword."""

    keyword_list = [keyword.lower() for keyword in _normalize(keywords)]
    if not keyword_list:
        return list(jobs)
    result: list[Mapping[str, object]] = []
    for job in jobs:
        title = str(job.get("title", "")).lower()
        if any(keyword in title for keyword in keyword_list):
            result.append(job)
    return result
