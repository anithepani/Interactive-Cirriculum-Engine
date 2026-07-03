"""Shared LLM client abstraction (Hybrid strategy, locked decision #1).

GPT-4o for high-value generation, grading, and structured reasoning; Llama 3.1
70B / Qwen2.5-Coder for bulk tasks, fallback, and the sovereignty path.

Responsibilities:
- Route to the right model based on task tier (high-value vs bulk vs code-heavy)
- Enforce per-curriculum token budgets (cost control, risk E16)
- Cache responses (embeddings, transcripts, identical prompts)
- Provide structured-output helpers (function calling / JSON schema)
- Trigger fallback (degradation §6.4) when GPT-4o is unavailable/over budget

Owner: Aryan. Consumed by all libs/ai/* generation + evaluation packages.
"""
from __future__ import annotations

from typing import Any, Literal


class LLMClient:
    """Routes between GPT-4o (primary) and Llama/Qwen (fallback) per task tier."""

    def complete(
        self,
        prompt: str,
        *,
        tier: Literal["high_value", "bulk", "code"] = "bulk",
        response_schema: dict | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Return a structured completion. Falls back per the Hybrid strategy."""
        raise NotImplementedError("Phase 0/1 deliverable - see prompt-library/")


_client: LLMClient | None = None


def get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
