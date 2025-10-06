"""Tests for scoring utilities."""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from app.matching.scorer import score


def test_score_monotonicity() -> None:
    """Ensure that relevant job text scores higher than unrelated text."""

    profile_skills = "Experienced WordPress engineer with PHP and WooCommerce expertise."
    keywords = ["WordPress", "PHP", "WooCommerce"]

    relevant_job = (
        "We are hiring a WordPress developer with PHP knowledge to build WooCommerce stores."
    )
    unrelated_job = "Seeking a logistics manager with supply chain experience."

    relevant_score = score(relevant_job, profile_skills, keywords)
    unrelated_score = score(unrelated_job, profile_skills, keywords)

    assert relevant_score.score > unrelated_score.score
    assert relevant_score.cosine_similarity >= unrelated_score.cosine_similarity


def test_score_keyword_influence() -> None:
    """Keyword hits should influence the final score and appear in the breakdown."""

    profile_skills = "Software engineer focusing on content management systems."
    keywords = ["WordPress", "PHP"]

    keyword_job = "This role requires WordPress customization and PHP integrations."
    neutral_job = "This role involves Python scripting and data analysis."

    keyword_result = score(keyword_job, profile_skills, keywords)
    neutral_result = score(neutral_job, profile_skills, keywords)

    assert keyword_result.keyword_weight >= neutral_result.keyword_weight
    assert "WordPress" in keyword_result.matched_keywords
