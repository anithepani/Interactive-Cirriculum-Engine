"""Gemini-backed LLM client.

Uses gemini-3.5-flash via the OpenAI compatibility endpoint to bypass Groq rate limits.
"""

from __future__ import annotations

import logging
import os
import random
import time

from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

load_dotenv()

from ice_shared.settings import settings  # noqa: E402

logger = logging.getLogger(__name__)

# Use Gemini by default for speed
MODEL = "gemini-3.5-flash"
MAX_RETRIES = max(0, int(settings.groq_max_retries))
BACKOFF_INITIAL = max(0.1, float(settings.groq_backoff_initial))
BACKOFF_CAP_SEC = 60.0


def _retry_after_seconds(exc: RateLimitError) -> float | None:
    """Extract a ``Retry-After`` hint (seconds) from the 429 response, if any."""
    try:
        headers = getattr(getattr(exc, "response", None), "headers", None) or {}
        raw = headers.get("retry-after") or headers.get("Retry-After")
        if raw is None:
            return None
        return float(raw)
    except (TypeError, ValueError):
        return None


def _backoff_delay(attempt: int, exc: RateLimitError) -> float:
    """Compute the sleep before the next attempt."""
    server_hint = _retry_after_seconds(exc)
    if server_hint is not None:
        return min(server_hint, BACKOFF_CAP_SEC) + random.uniform(0, BACKOFF_INITIAL)
    base = BACKOFF_INITIAL * (2 ** attempt)
    return min(base, BACKOFF_CAP_SEC) + random.uniform(0, BACKOFF_INITIAL)


class LLMClient:
    """Thin client around the OpenAI SDK configured for Gemini."""

    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set in the environment. "
                "Export it before constructing LLMClient."
            )
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            max_retries=0
        )

    def complete(
        self,
        prompt: str,
        tier: str = "high_value",
        system: str | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error: RateLimitError | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                )
                return response.choices[0].message.content
            except RateLimitError as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = _backoff_delay(attempt, exc)
                    logger.warning(
                        "Gemini 429 rate-limit (attempt %d/%d); backing off %.2fs",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)

        assert last_error is not None
        raise last_error


_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Return a process-wide singleton LLMClient."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
