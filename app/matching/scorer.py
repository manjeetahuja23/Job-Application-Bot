"""Scoring utilities for job matching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from numpy.typing import NDArray

from app.core.config import get_settings


@dataclass(slots=True)
class ScoreResult:
    """Structured score output for a job/profile comparison."""

    score: float
    cosine_similarity: float
    keyword_weight: float
    matched_keywords: list[str]


def cosine_similarity(vector_a: NDArray[np.float64], vector_b: NDArray[np.float64]) -> float:
    """Return cosine similarity between two vectors."""

    denom = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denom)


def _normalize_keywords(keywords: Iterable[str]) -> list[str]:
    return [keyword.strip() for keyword in keywords if keyword and keyword.strip()]


def _keyword_hits(text: str, keywords: Sequence[str]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for keyword in keywords:
        if keyword.lower() in lowered:
            hits.append(keyword)
    return hits


def score(
    job_text: str,
    profile_skills: str,
    keywords_list: Sequence[str],
    *,
    job_vector: NDArray[np.float64] | None = None,
    profile_vector: NDArray[np.float64] | None = None,
) -> ScoreResult:
    """Calculate a weighted score for a job given profile skills and keywords."""

    keywords = _normalize_keywords(keywords_list)
    keyword_hits = _keyword_hits(job_text, keywords)
    keyword_ratio = (len(keyword_hits) / len(keywords)) if keywords else 0.0

    if job_vector is None or profile_vector is None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([job_text, profile_skills]).toarray()
        job_vector = matrix[0]
        profile_vector = matrix[1]

    cosine = cosine_similarity(np.asarray(job_vector, dtype=np.float64), np.asarray(profile_vector, dtype=np.float64))

    settings = get_settings()
    cosine_weight = getattr(settings, "cosine_weight", 0.6)
    keyword_weight_setting = getattr(settings, "keyword_weight", 0.4)

    final = cosine_weight * cosine + keyword_weight_setting * keyword_ratio
    final = max(0.0, min(1.0, final))

    return ScoreResult(
        score=final,
        cosine_similarity=cosine,
        keyword_weight=keyword_ratio,
        matched_keywords=keyword_hits,
    )
