"""Salary extraction helpers."""
from __future__ import annotations

import re
from typing import Optional, Tuple

_RANGE_PATTERN = re.compile(
    r"\$(?P<low>\d[\d,]*(?:\.\d+)?)\s*(?P<lowsuffix>[kK])?\s*(?:-|–|—|to)\s*\$(?P<high>\d[\d,]*(?:\.\d+)?)\s*(?P<highsuffix>[kK])?",
    re.IGNORECASE,
)
_SINGLE_PATTERN = re.compile(r"\$(?P<value>\d[\d,]*(?:\.\d+)?)(?P<suffix>[kK])?", re.IGNORECASE)


def _to_int(value: str, suffix: str | None) -> int:
    number = float(value.replace(",", ""))
    if suffix and suffix.lower() == "k":
        number *= 1000
    return int(round(number))


def extract_salary_range(text: str) -> Optional[Tuple[int, int]]:
    """Return a salary range detected within text."""

    if not text:
        return None

    match = _RANGE_PATTERN.search(text)
    if match:
        low = _to_int(match.group("low"), match.group("lowsuffix"))
        high = _to_int(match.group("high"), match.group("highsuffix"))
        if high < low:
            low, high = high, low
        return (low, high)

    singles = list(_SINGLE_PATTERN.finditer(text))
    if not singles:
        return None

    first = singles[0]
    value = _to_int(first.group("value"), first.group("suffix"))
    return (value, value)
