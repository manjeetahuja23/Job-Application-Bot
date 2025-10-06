"""Text processing helpers."""
from __future__ import annotations

import re
from typing import Iterable


def clean_whitespace(value: str) -> str:
    """Collapse multiple whitespace characters into single spaces."""

    return re.sub(r"\s+", " ", value).strip()


def contains_keywords(text: str, keywords: Iterable[str]) -> bool:
    """Check if any keyword is present in the text (case-insensitive)."""

    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)
