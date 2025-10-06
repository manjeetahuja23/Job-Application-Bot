"""HTML sanitization utilities."""
from __future__ import annotations

from bs4 import BeautifulSoup


def clean_html(html: str) -> str:
    """Remove HTML tags while preserving paragraph and bullet structure."""

    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()

    lines: list[str] = []
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if text:
            lines.append(f"- {text}")
        li.decompose()

    text = soup.get_text("\n", strip=True)
    for line in text.splitlines():
        normalized = " ".join(line.split())
        if normalized:
            lines.append(normalized)

    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        if line not in seen:
            deduped.append(line)
            seen.add(line)

    return "\n".join(deduped)
