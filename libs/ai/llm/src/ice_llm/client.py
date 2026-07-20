"""Groq-backed LLM client (Phase 0 / Week 1).

Uses llama-3.3-70b-versatile on Groq (free tier). This is the first concrete
implementation of the Hybrid LLM strategy (ADR 0001); GPT-4o routing lands later.
"""

from __future__ import annotations

import logging
import os
import random
import time

from groq import Groq, RateLimitError
from dotenv import load_dotenv

load_dotenv()

from ice_shared.settings import settings  # noqa: E402

logger = logging.getLogger(__name__)

MODEL = settings.groq_model or "llama-3.3-70b-versatile"
# Exponential-backoff config (429 rate-limit handling). Configurable via
# GROQ_MAX_RETRIES / GROQ_BACKOFF_INITIAL. Defaults are more lenient than the
# old fixed 5s x2 loop, so 429s recover instead of failing the pipeline.
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
    """Compute the sleep before the next attempt.

    Honors the server's ``Retry-After`` header when present; otherwise uses
    exponential backoff with full jitter:
        base = BACKOFF_INITIAL * 2**attempt
        delay = min(base, cap) + random.uniform(0, BACKOFF_INITIAL)
    """
    server_hint = _retry_after_seconds(exc)
    if server_hint is not None:
        return min(server_hint, BACKOFF_CAP_SEC) + random.uniform(0, BACKOFF_INITIAL)
    base = BACKOFF_INITIAL * (2 ** attempt)
    return min(base, BACKOFF_CAP_SEC) + random.uniform(0, BACKOFF_INITIAL)


class LLMClient:
    """Thin client around the Groq SDK for the locked Phase-0 model."""

    def __init__(self) -> None:
        api_key = (settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")).strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set in the environment. "
                "Export it before constructing LLMClient."
            )
        # max_retries=0: disable the SDK's own internal retry so our single,
        # jittered exponential backoff below is the only retry path (no
        # double-stacking of backoffs).
        self.client = Groq(api_key=api_key, max_retries=0)

    def complete(
        self,
        prompt: str,
        tier: str = "high_value",
        system: str | None = None,
    ) -> str:
        """Return the model's text completion for `prompt`.

        `tier` is accepted for forward-compatibility with the Hybrid routing
        (ADR 0001) but does not change routing in this Phase-0 build; every
        call goes to llama-3.3-70b-versatile on Groq.

        Retries up to `MAX_RETRIES` times on `RateLimitError` using exponential
        backoff with full jitter (honoring the server's ``Retry-After`` header
        when present). Any other exception is raised immediately.
        """
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
                        "Groq 429 rate-limit (attempt %d/%d); backing off %.2fs",
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
