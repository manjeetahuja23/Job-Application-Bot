"""Unit tests for text utilities."""
from __future__ import annotations

from app.utils.text import clean_whitespace, contains_keywords


def test_clean_whitespace() -> None:
    """Whitespace should be collapsed to single spaces."""

    assert clean_whitespace("Hello\nWorld") == "Hello World"


def test_contains_keywords() -> None:
    """Should detect keywords irrespective of case."""

    assert contains_keywords("Python developer", ["python"]) is True
    assert contains_keywords("Python developer", ["java"]) is False
