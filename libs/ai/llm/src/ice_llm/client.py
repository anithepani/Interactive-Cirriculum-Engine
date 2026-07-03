"""Groq-backed LLM client (Phase 0 / Week 1).

Uses llama-3.3-70b-versatile on Groq (free tier). This is the first concrete
implementation of the Hybrid LLM strategy (ADR 0001); GPT-4o routing lands later.
"""

from __future__ import annotations

import os
import time

from groq import Groq, RateLimitError

MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2
RETRY_SLEEP_SEC = 5


class LLMClient:
    """Thin client around the Groq SDK for the locked Phase-0 model."""

    def __init__(self) -> None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set in the environment. "
                "Export it before constructing LLMClient."
            )
        self.client = Groq(api_key=api_key)

    def complete(
        self,
        prompt: str,
        tier: str = "high_value",
        system: str | None = None,
    ) -> str:
        """Return the model's text completion for `prompt`.

        `tier` is accepted for forward-compatibility with the Hybrid routing
        (ADR 0001) but does not change routing in this Phase-0 build; every
        call goes to llama-3.1-70b-versatile on Groq.

        Retries up to `MAX_RETRIES` times on `RateLimitError`, sleeping
        `RETRY_SLEEP_SEC` seconds between attempts. Any other exception is
        raised immediately.
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
                    time.sleep(RETRY_SLEEP_SEC)

        assert last_error is not None
        raise last_error


_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Return a process-wide singleton LLMClient."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
