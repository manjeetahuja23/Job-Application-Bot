"""Document export helpers."""
from __future__ import annotations

from pathlib import Path


def _write(content: str, output_path: Path) -> Path:
    """Persist rendered content to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def export_markdown(content: str, output_path: Path) -> Path:
    """Persist a Markdown document."""

    if output_path.suffix != ".md":
        output_path = output_path.with_suffix(".md")
    return _write(content, output_path)


def export_text(content: str, output_path: Path) -> Path:
    """Persist a plain-text document."""

    if output_path.suffix != ".txt":
        output_path = output_path.with_suffix(".txt")
    return _write(content, output_path)


# TODO: Add export helpers for PDF and DOCX once binary dependencies are permitted.
