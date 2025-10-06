"""Application settings definitions."""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

_PYDANTIC_AVAILABLE = importlib.util.find_spec("pydantic") is not None

if _PYDANTIC_AVAILABLE:  # pragma: no cover - exercised when dependency installed
    from pydantic import AnyUrl, EmailStr, Field, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict


    class AppSettings(BaseSettings):
        """Settings loaded from environment variables."""

        database_url: str
        redis_url: AnyUrl | str
        app_secret: str
        timezone: str
        email_from: EmailStr
        email_smtp_host: str
        email_smtp_user: str | None = None
        email_smtp_pass: str | None = None
        telegram_bot_token: str | None = None
        telegram_chat_id: str | None = None
        default_profile_name: str = ""
        match_keywords: List[str] = Field(default_factory=list)
        title_keywords: List[str] = Field(
            default_factory=lambda: ["WordPress", "PHP", "JavaScript", "WooCommerce"]
        )
        geo_filter_keywords: List[str] = Field(
            default_factory=lambda: ["Remote", "Canada", "United States", "US"]
        )
        min_score: float = 0.0
        cosine_weight: float = 0.6
        keyword_weight: float = 0.4
        playwright_headless: bool = True
        celery_eager: bool = Field(default_factory=lambda: os.getenv("CELERY_EAGER", "true").lower() == "true")

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

        @field_validator("match_keywords", mode="before")
        @classmethod
        def _split_keywords(cls, value: str | List[str]) -> List[str]:
            """Ensure comma-separated keywords are converted into a list."""

            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            return value

        @field_validator("title_keywords", "geo_filter_keywords", mode="before")
        @classmethod
        def _split_additional_keywords(cls, value: str | List[str]) -> List[str]:
            """Convert additional keyword configuration into lists."""

            return cls._split_keywords(value)

        @classmethod
        def from_env(cls) -> "AppSettings":
            """Load settings using cached environment lookup."""

            return _get_settings()


else:

    def _split_keywords(value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)


    @dataclass(slots=True)
    class AppSettings:  # type: ignore[redeclaration]
        """Settings loaded from environment variables without Pydantic."""

        database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./autojob.db"))
        redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        app_secret: str = field(default_factory=lambda: os.getenv("APP_SECRET", "change-me"))
        timezone: str = field(default_factory=lambda: os.getenv("TIMEZONE", "UTC"))
        email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", "noreply@example.com"))
        email_smtp_host: str = field(default_factory=lambda: os.getenv("EMAIL_SMTP_HOST", "localhost"))
        email_smtp_user: str | None = field(default_factory=lambda: os.getenv("EMAIL_SMTP_USER") or None)
        email_smtp_pass: str | None = field(default_factory=lambda: os.getenv("EMAIL_SMTP_PASS") or None)
        telegram_bot_token: str | None = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN") or None)
        telegram_chat_id: str | None = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID") or None)
        default_profile_name: str = field(default_factory=lambda: os.getenv("DEFAULT_PROFILE_NAME", ""))
        match_keywords: List[str] = field(default_factory=list)
        title_keywords: List[str] = field(default_factory=list)
        geo_filter_keywords: List[str] = field(default_factory=list)
        min_score: float = field(default_factory=lambda: float(os.getenv("MIN_SCORE", "0.0")))
        cosine_weight: float = field(default_factory=lambda: float(os.getenv("COSINE_WEIGHT", "0.6")))
        keyword_weight: float = field(default_factory=lambda: float(os.getenv("KEYWORD_WEIGHT", "0.4")))
        playwright_headless: bool = field(
            default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
        )
        celery_eager: bool = field(
            default_factory=lambda: os.getenv("CELERY_EAGER", "true").lower() == "true"
        )

        def __post_init__(self) -> None:
            raw_keywords = os.getenv("MATCH_KEYWORDS", "")
            if raw_keywords:
                self.match_keywords = _split_keywords(raw_keywords)
            elif not self.match_keywords:
                self.match_keywords = [
                    "wordpress",
                    "php",
                    "javascript",
                    "woocommerce",
                    "react",
                    "api",
                    "rest",
                ]

            raw_title = os.getenv("TITLE_KEYWORDS")
            if raw_title:
                self.title_keywords = _split_keywords(raw_title)
            elif not self.title_keywords:
                self.title_keywords = ["WordPress", "PHP", "JavaScript", "WooCommerce"]

            raw_geo = os.getenv("GEO_FILTER_KEYWORDS")
            if raw_geo:
                self.geo_filter_keywords = _split_keywords(raw_geo)
            elif not self.geo_filter_keywords:
                self.geo_filter_keywords = ["Remote", "Canada", "United States", "US"]

        @classmethod
        def from_env(cls) -> "AppSettings":
            """Load settings using cached environment lookup."""

            return _get_settings()


@lru_cache(maxsize=1)
def _get_settings() -> AppSettings:
    """Internal cache for settings to avoid repeated parsing."""

    if _PYDANTIC_AVAILABLE:
        return AppSettings()  # type: ignore[arg-type]
    return AppSettings()
