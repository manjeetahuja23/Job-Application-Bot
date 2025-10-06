"""Seed routines for the application database."""
from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Profile
from app.db.session import session_scope


def seed_default_profile() -> None:
    """Ensure a default profile exists for matching workflows."""

    settings = get_settings()
    profile_name = settings.default_profile_name
    if not profile_name:
        raise ValueError("DEFAULT_PROFILE_NAME must be configured before seeding.")

    keywords = ",".join(settings.match_keywords)
    with session_scope() as session:
        existing = session.execute(
            select(Profile).where(Profile.name == profile_name)
        ).scalar_one_or_none()
        if existing is not None:
            return

        profile = Profile(
            name=profile_name,
            skills="WordPress, PHP, JavaScript, WooCommerce, REST APIs",
            keywords=keywords,
            geo_preference="Remote, Canada, US",
            salary_min=None,
            salary_max=None,
            resume_template_path="app/docs/templates/resume_base.md",
            cover_template_path="app/docs/templates/cover_base.md",
        )
        session.add(profile)


def main() -> None:
    """Entry-point for CLI execution."""

    seed_default_profile()


if __name__ == "__main__":
    main()
