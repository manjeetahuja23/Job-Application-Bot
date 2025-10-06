"""HTTP utilities for making network requests."""
from __future__ import annotations

import time
from typing import Any

import httpx


_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class HttpClient:
    """Simple wrapper around httpx for reusable configuration."""

    def __init__(self, timeout: float = 10.0, user_agent: str | None = None) -> None:
        headers = {"User-Agent": user_agent or "autojob-bot/0.1"}
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout, headers=headers, follow_redirects=True)

    def __enter__(self) -> "HttpClient":
        """Enter context manager and return self."""

        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        """Close the client when exiting context manager."""

        self.close()

    def get(self, url: str, *, headers: dict[str, str] | None = None, max_retries: int = 3) -> httpx.Response:
        """Perform a GET request with simple exponential backoff."""

        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.get(url, headers=headers)
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:  # pragma: no cover - network error path
                last_exc = exc
                status_code = getattr(exc.response, "status_code", None)
                if status_code not in _RETRYABLE_STATUS_CODES or attempt >= max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2
        if last_exc:  # pragma: no cover - defensive
            raise last_exc
        raise RuntimeError("GET request failed without raising an exception")

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        """Perform a GET request and return the JSON payload."""

        response = self.get(url, headers=headers)
        return response.json()

    def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        """Perform a GET request and return the text payload."""

        response = self.get(url, headers=headers)
        return response.text

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()
