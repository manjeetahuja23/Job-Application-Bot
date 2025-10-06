"""Settings endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.ui import templates
from app.db import models
from app.db.session import get_session
from app.db.utils import get_default_profile

router = APIRouter()


class ProfileSettingsPayload(BaseModel):
    """Schema for updating profile settings."""

    skills: str
    keywords: str
    geo_preference: str
    salary_min: int | None = None
    salary_max: int | None = None


def _wants_html(request: Request) -> bool:
    if request.headers.get("hx-request") == "true":
        return True
    accept = request.headers.get("accept", "")
    return "text/html" in accept or "application/xhtml+xml" in accept


def _serialize_profile(profile: models.Profile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "skills": profile.skills,
        "keywords": profile.keywords,
        "geo_preference": profile.geo_preference,
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
    }


@router.get("/settings")
async def read_settings(
    request: Request,
    db: Session = Depends(get_session),
):
    """Return profile settings for JSON clients or render the settings form."""

    profile = get_default_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    payload = _serialize_profile(profile)
    if _wants_html(request):
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "profile": payload,
            },
        )

    return payload


@router.post("/settings")
async def update_settings(
    request: Request,
    db: Session = Depends(get_session),
):
    """Persist updated profile settings from JSON or HTML form submissions."""

    profile = get_default_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded"):
        form = await request.form()

        def _optional_int(value: str | None) -> int | None:
            return int(value) if value and value.strip() else None

        payload = ProfileSettingsPayload(
            skills=str(form.get("skills", profile.skills)),
            keywords=str(form.get("keywords", profile.keywords)),
            geo_preference=str(form.get("geo_preference", profile.geo_preference)),
            salary_min=_optional_int(form.get("salary_min")),
            salary_max=_optional_int(form.get("salary_max")),
        )
    else:
        data = await request.json()
        payload = ProfileSettingsPayload.model_validate(data)

    profile.skills = payload.skills
    profile.keywords = payload.keywords
    profile.geo_preference = payload.geo_preference
    profile.salary_min = payload.salary_min
    profile.salary_max = payload.salary_max

    db.add(profile)
    db.commit()
    db.refresh(profile)

    serialized = _serialize_profile(profile)
    if content_type.startswith("application/x-www-form-urlencoded") or _wants_html(request):
        return templates.TemplateResponse(
            "settings.html",
            {"request": request, "profile": serialized, "saved": True},
        )

    return serialized
