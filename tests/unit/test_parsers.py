"""Parser unit tests."""
from __future__ import annotations

import pytest

pytest.importorskip("bs4")

from app.parsing.clean_html import clean_html
from app.parsing.extract_salary import extract_salary_range


def test_clean_html_preserves_bullets() -> None:
    """Bulleted HTML should be converted into text with hyphen bullets."""

    html = """
    <div>
        <p>Intro paragraph.</p>
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
    </div>
    """
    cleaned = clean_html(html)
    lines = cleaned.splitlines()
    assert "Intro paragraph." in lines
    assert "- First item" in lines
    assert "- Second item" in lines


def test_extract_salary_range_detects_range() -> None:
    """Salary ranges should be parsed into integer tuples."""

    text = "Compensation: $85k - $105k USD depending on experience."
    assert extract_salary_range(text) == (85000, 105000)


def test_extract_salary_range_single_value() -> None:
    """Single salaries should be returned as a flat range."""

    text = "Base pay is $120000 plus benefits."
    assert extract_salary_range(text) == (120000, 120000)
