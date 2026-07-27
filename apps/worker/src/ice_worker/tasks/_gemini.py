"""Shared Gemini client helper: dynamic model selection with fallback.

Avoids hardcoding a (likely-invalid) model name, which silently broke the
signal-video task: ``GenerativeModel("gemini-3.1-flash-lite")`` raised when that
exact name was not served, the exception was swallowed, and the task ended with
no trace. Mirrors ``recap``'s ``list_models()`` + preferred-candidate
selection so both tasks share one robust path.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Preferred models in priority order. The first one served by the API wins;
# if none are available we fall back to the first content-capable model.
_PREFERRED_MODELS = (
    "models/gemini-3.1-flash-lite",
    "models/gemini-3.5-flash",
    "models/gemini-3.1-pro-preview",
    "models/gemini-flash-latest",
)


def get_gemini_model(generation_config: dict[str, Any] | None = None) -> Any:
    """Configure Gemini and return a ``GenerativeModel`` selected via ``list_models()``.

    Falls back to the first available content-capable model if none of the
    preferred names are served. Raises ``ValueError`` when the API key is unset
    or no content model is available at all, so failures are loud instead of
    silent.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    api_key = api_key.strip()

    genai.configure(api_key=api_key, transport="rest")

    available_models = [
        m.name
        for m in genai.list_models()
        if "generateContent" in m.supported_generation_methods
    ]
    if not available_models:
        raise ValueError("No Gemini models supporting generateContent were found")

    target_model = None
    for preferred in _PREFERRED_MODELS:
        if preferred in available_models:
            target_model = preferred.replace("models/", "")
            break

    if not target_model:
        target_model = available_models[0].replace("models/", "")
        logger.warning(
            "No preferred Gemini model available; falling back to %s",
            target_model,
        )

    logger.info("Using Gemini model: %s", target_model)
    try:
        if generation_config is not None:
            return genai.GenerativeModel(target_model, generation_config=generation_config)
        return genai.GenerativeModel(target_model)
    except Exception:
        # Some models reject generation_config (e.g. response_mime_type); retry bare.
        return genai.GenerativeModel(target_model)
