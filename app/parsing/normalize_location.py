"""Location normalization helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

REMOTE_KEYWORDS = ("remote", "anywhere", "distributed")
HYBRID_KEYWORDS = ("hybrid", "flexible")


@dataclass(frozen=True)
class LocationDetails:
    """Structured representation of a job location."""

    raw: str
    normalized: str
    city: str | None
    region: str | None
    country: str | None
    kind: str
    is_remote: bool


def _tokenise(location: str) -> Iterable[str]:
    for token in re.split(r"[,/|]", location):
        token = token.strip()
        if token:
            yield token


def normalize_location(location: str) -> LocationDetails:
    """Detect remote status and split a location string into components."""

    raw = (location or "").strip()
    lowered = raw.lower()
    is_remote = any(keyword in lowered for keyword in REMOTE_KEYWORDS)
    is_hybrid = not is_remote and any(keyword in lowered for keyword in HYBRID_KEYWORDS)
    kind = "remote" if is_remote else "hybrid" if is_hybrid else "on-site"

    tokens = list(_tokenise(raw))
    city = tokens[0] if tokens else None
    region = tokens[1] if len(tokens) > 1 else None
    country = tokens[2] if len(tokens) > 2 else None

    if not tokens and is_remote:
        normalized = "Remote"
    elif tokens:
        normalized = ", ".join(dict.fromkeys(tokens))
    else:
        normalized = "Unknown"

    if kind == "hybrid" and normalized != "Unknown":
        normalized = f"Hybrid - {normalized}"
    elif is_remote and normalized != "Remote":
        normalized = f"Remote - {normalized}"

    return LocationDetails(
        raw=raw,
        normalized=normalized,
        city=city,
        region=region,
        country=country,
        kind=kind,
        is_remote=is_remote,
    )
