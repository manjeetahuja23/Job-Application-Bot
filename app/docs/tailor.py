"""Document tailoring utilities."""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models
from app.docs import exports

TEMPLATES_PATH = Path(__file__).resolve().parent / "templates"
ACHIEVEMENTS_PATH = Path(__file__).resolve().parent / "achievements_demo.json"
DEFAULT_STORAGE_ROOT = Path("storage") / "documents"
_STOPWORDS = {
    "and",
    "for",
    "with",
    "that",
    "from",
    "this",
    "your",
    "have",
    "will",
    "work",
    "team",
    "role",
    "skills",
    "experience",
    "ability",
    "using",
    "into",
    "across",
    "their",
    "about",
    "more",
    "when",
    "where",
    "which",
    "while",
}


@dataclass
class TailorResult:
    """Result of tailoring a set of documents for a job/profile pair."""

    document: models.Document
    resume_path: Path
    cover_path: Path
    keywords: list[str]
    achievements: list[str]


@lru_cache(maxsize=1)
def _load_achievements() -> dict[str, str]:
    """Load canned achievement snippets from disk."""

    if not ACHIEVEMENTS_PATH.exists():
        return {}
    data = json.loads(ACHIEVEMENTS_PATH.read_text(encoding="utf-8"))
    return {key.lower(): value for key, value in data.items()}


def _render_template(name: str, context: dict[str, str]) -> str:
    """Render a template by replacing ``{{TOKEN}}`` placeholders."""

    template_path = TEMPLATES_PATH / name
    content = template_path.read_text(encoding="utf-8")
    rendered = content
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    rendered = re.sub(r"\{\{[^}]+\}\}", "", rendered)
    return rendered.strip() + "\n"


def build_resume(context: dict[str, str]) -> str:
    """Render the resume template with sane defaults."""

    settings = get_settings()
    base_context = {
        "NAME": settings.default_profile_name,
        "ROLE": context.get("ROLE", "Software Developer"),
        "COMPANY": context.get("COMPANY", "An Outstanding Company"),
        "KEYWORDS": context.get("KEYWORDS", "Collaboration, Automation"),
        "ACHIEVEMENTS": context.get("ACHIEVEMENTS", "- Delivered measurable value."),
        "SKILLS": context.get("SKILLS", "Python, Automation, APIs, Communication"),
    }
    base_context.update(context)
    return _render_template("resume_base.md", base_context)


def build_cover_letter(context: dict[str, str]) -> str:
    """Render the cover letter template with sensible defaults."""

    settings = get_settings()
    base_context = {
        "NAME": settings.default_profile_name,
        "ROLE": context.get("ROLE", "Software Developer"),
        "COMPANY": context.get("COMPANY", "Your Team"),
        "KEYWORDS": context.get("KEYWORDS", "automation, collaboration"),
        "ACHIEVEMENTS": context.get("ACHIEVEMENTS", "- Delivered measurable value."),
    }
    base_context.update(context)
    return _render_template("cover_base.md", base_context)


def _display_keyword(value: str) -> str:
    """Format a keyword for human-friendly output."""

    stripped = value.strip()
    if not stripped:
        return stripped
    if len(stripped) <= 3:
        return stripped.upper()
    if any(char.isupper() for char in stripped[1:]):
        return stripped
    return stripped.capitalize()


def _extract_from_text(text: str, limit: int, seen: set[str]) -> list[tuple[str, str]]:
    """Extract keywords from the job description text."""

    words = re.findall(r"[A-Za-z][A-Za-z0-9+/#-]*", text.lower())
    counter = Counter(words)
    results: list[tuple[str, str]] = []
    for word, _ in counter.most_common():
        if len(word) < 3 or word in _STOPWORDS:
            continue
        if word in seen:
            continue
        seen.add(word)
        results.append((word, _display_keyword(word)))
        if len(seen) >= limit:
            break
    return results


def derive_keywords(job: models.Job, limit: int = 10) -> list[tuple[str, str]]:
    """Derive a ranked list of keywords for the supplied job."""

    seen: set[str] = set()
    keywords: list[tuple[str, str]] = []

    if job.tags:
        for raw_tag in job.tags.split(","):
            tag = raw_tag.strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            keywords.append((key, _display_keyword(tag)))
            if len(seen) >= limit:
                return keywords

    text_source = job.description_text or job.description_html or ""
    keywords.extend(_extract_from_text(text_source, limit, seen))
    return keywords[:limit]


def _achievements_for_keywords(keywords: Iterable[tuple[str, str]]) -> list[str]:
    """Return canned achievements for the provided keywords."""

    catalog = _load_achievements()
    achievements: list[str] = []
    for key, _display in keywords:
        achievement = catalog.get(key)
        if achievement and achievement not in achievements:
            achievements.append(achievement)
    if not achievements:
        achievements.append("Delivered measurable improvements across engineering and automation initiatives.")
    return achievements


def _build_context(job: models.Job, profile: models.Profile, keywords: Sequence[tuple[str, str]], achievements: Sequence[str]) -> dict[str, str]:
    """Build template context from the job, profile, and derived metadata."""

    display_keywords = ", ".join(display for _, display in keywords) or "Collaboration, Automation"
    achievement_block = "\n".join(f"- {achievement}" for achievement in achievements)
    skills = profile.skills if profile.skills else "Automation, Collaboration"
    return {
        "NAME": profile.name,
        "ROLE": job.title,
        "COMPANY": job.company,
        "KEYWORDS": display_keywords,
        "ACHIEVEMENTS": achievement_block,
        "SKILLS": skills,
    }


def tailor_job_documents(
    session: Session,
    job: models.Job,
    profile: models.Profile,
    *,
    storage_root: Path | None = None,
) -> TailorResult:
    """Tailor resume and cover letter documents for a job/profile pairing."""

    keywords = derive_keywords(job)
    achievements = _achievements_for_keywords(keywords)
    context = _build_context(job, profile, keywords, achievements)

    resume_content = build_resume(context)
    cover_content = build_cover_letter(context)

    base_dir = (storage_root or DEFAULT_STORAGE_ROOT) / str(job.id)
    resume_path = exports.export_markdown(resume_content, base_dir / "resume.md")
    exports.export_text(resume_content, base_dir / "resume.txt")
    cover_path = exports.export_markdown(cover_content, base_dir / "cover.md")
    exports.export_text(cover_content, base_dir / "cover.txt")

    existing = session.execute(
        select(models.Document).where(
            models.Document.job_id == job.id,
            models.Document.profile_id == profile.id,
        )
    ).scalar_one_or_none()

    if existing is None:
        document = models.Document(
            job_id=job.id,
            profile_id=profile.id,
            resume_path=str(resume_path),
            cover_path=str(cover_path),
        )
        session.add(document)
    else:
        existing.resume_path = str(resume_path)
        existing.cover_path = str(cover_path)
        document = existing

    session.flush()
    session.refresh(document)

    return TailorResult(
        document=document,
        resume_path=resume_path,
        cover_path=cover_path,
        keywords=[display for _, display in keywords],
        achievements=list(achievements),
    )


def tailor_job_by_id(
    session: Session,
    job_id: uuid.UUID | str,
    profile_id: int,
    *,
    storage_root: Path | None = None,
) -> TailorResult:
    """Helper that loads models and tailors documents in one call."""

    job = session.get(models.Job, job_id)
    if job is None:
        raise ValueError("Job not found for tailoring.")
    profile = session.get(models.Profile, profile_id)
    if profile is None:
        raise ValueError("Profile not found for tailoring.")
    return tailor_job_documents(session, job, profile, storage_root=storage_root)
