"""Shared LLM client abstraction (Hybrid strategy, locked decision #1).

Phase-0 implementation routes every call to llama-3.1-70b-versatile on Groq
(see client.py). GPT-4o + Llama/Qwen routing lands in a later phase.

Owner: Aryan. Consumed by all libs/ai/* generation + evaluation packages.
"""
from __future__ import annotations

from ice_llm.client import LLMClient, get_client

__all__ = ["LLMClient", "get_client"]
__version__ = "0.1.0"
