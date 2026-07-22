"""Phase 5 content classifier.

Classifies a curriculum's overall content into a coarse category so downstream
stages (M6 checkpoint placement, M7 exercise generation) can dynamically pick
exercise types that actually fit the video — instead of a hardcoded rotation.

Categories:
    - ``programming``   : code-heavy technical lessons (coding/debug appropriate)
    - ``theory``        : formal/academic content best tested with mcq/conceptual
    - ``conceptual``    : idea/explanatory content best tested with conceptual/mcq
    - ``motivational``  : speeches / inspiration (light conceptual/mcq only)
    - ``mixed``         : a blend — all exercise types allowed

Design:
    - One LLM call per curriculum (lightweight, called once). Reuses
      ``ice_llm.get_client``.
    - Robust keyword fallback for when the LLM is unavailable or returns an
      unparseable/unknown answer, so classification never breaks the pipeline.

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = ("programming", "theory", "conceptual", "motivational", "mixed")

# Keyword buckets for the offline fallback. Deliberately biased toward
# unambiguous signals so ordinary speech is not misclassified.
_PROGRAMMING_KEYWORDS = (
    "def ", "def(", "class ", "class(", "import ", "function", "variable",
    "return ", "for loop", "while loop", "array", "list", "dictionary",
    "compiler", "syntax", "algorithm", "data structure", "recursion",
    "python", "javascript", "typescript", "java", "c++", "c#", "code",
    "coding", "program", "method", "parameter", "argument", "api",
    "database", "sql", "framework", "library", "module", "package",
    "debug", "exception", "object", "boolean", "integer", "string",
)
_MOTIVATIONAL_KEYWORDS = (
    "motivation", "motivate", "motivated", "inspire", "inspiration",
    "inspiring", "believe", "belief", "dream", "passion", "mindset",
    "never give up", "you can do", "success", "perseverance", "grit",
    "overcome", "achieve your", "potential",
)
_THEORY_KEYWORDS = (
    "theorem", "theory", "theoretical", "hypothesis", "proof", "axiom",
    "principle", "law of", "equation", "derivation", "formula", "define",
    "definition", "abstract", "framework of", "model of",
)

_SYSTEM = (
    "You are a content classifier. You MUST respond with ONLY a single valid "
    "JSON object — no markdown fences, no prose. It must have exactly two keys: "
    '"category" (one of "programming", "theory", "conceptual", "motivational", '
    '"mixed") and "confidence" (a float between 0 and 1).'
)


def _build_evidence(segments: list, concepts: list, transcript: str) -> str:
    """Assemble a compact evidence blob (titles/summaries/labels/transcript)."""
    parts: list[str] = []
    for seg in segments or []:
        if isinstance(seg, dict):
            for key in ("title", "summary"):
                val = seg.get(key)
                if val:
                    parts.append(str(val))
    for conc in concepts or []:
        if isinstance(conc, dict):
            for key in ("label", "description"):
                val = conc.get(key)
                if val:
                    parts.append(str(val))
    if transcript:
        parts.append(str(transcript))
    return " ".join(parts)


def _keyword_fallback(evidence: str) -> dict:
    """Offline classification when the LLM is unavailable/unparseable."""
    hay = (evidence or "").lower()
    if not hay.strip():
        # No signal at all — safest generic bucket.
        return {"category": "conceptual", "confidence": 0.3}

    prog = sum(1 for kw in _PROGRAMMING_KEYWORDS if kw in hay)
    motiv = sum(1 for kw in _MOTIVATIONAL_KEYWORDS if kw in hay)
    theory = sum(1 for kw in _THEORY_KEYWORDS if kw in hay)

    scores = {"programming": prog, "motivational": motiv, "theory": theory}
    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score == 0:
        # Nothing matched — default to conceptual (safe, non-technical).
        return {"category": "conceptual", "confidence": 0.4}

    # Detect a genuine blend: programming plus a strong non-technical signal.
    non_prog = motiv + theory
    if prog >= 2 and non_prog >= 2:
        return {"category": "mixed", "confidence": 0.5}

    total = prog + motiv + theory
    confidence = min(0.9, 0.5 + (best_score / max(total, 1)) * 0.4)
    return {"category": best, "confidence": round(confidence, 2)}


def _parse_llm_json(raw: str) -> dict | None:
    """Extract the ``{category, confidence}`` object from an LLM response."""
    if not raw:
        return None
    text = raw.strip()
    fence = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        if start != -1:
            text = text[start:]
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    category = str(data.get("category", "")).strip().lower()
    if category not in _VALID_CATEGORIES:
        return None
    try:
        confidence = float(data.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))
    return {"category": category, "confidence": confidence}


def classify_content(segments: list, concepts: list, transcript: str) -> dict:
    """Classify a curriculum's content into a coarse category.

    Called once per curriculum (lightweight). Attempts an LLM classification
    first and falls back to a deterministic keyword heuristic when the LLM is
    unavailable or returns an unusable answer, so it never breaks the pipeline.

    Args:
        segments: M4 segment dicts (``title``/``summary`` used as evidence).
        concepts: M5 concept dicts or a graph dict (``label``/``description``).
        transcript: The full or partial transcript text.

    Returns:
        ``{"category": <one of programming|theory|conceptual|motivational|mixed>,
           "confidence": <float 0-1>}``.
    """
    # Accept a concept-graph dict as well as a bare list.
    if isinstance(concepts, dict):
        concepts_list = concepts.get("concepts", []) or []
    else:
        concepts_list = concepts or []

    evidence = _build_evidence(segments, concepts_list, transcript)

    try:
        from ice_llm import get_client

        client = get_client()
        prompt = (
            "Classify the following educational video content into exactly one "
            "category based on its dominant subject matter.\n\n"
            "Categories:\n"
            '- "programming": teaches code, software, or technical implementation.\n'
            '- "theory": formal/academic theory, proofs, definitions, principles.\n'
            '- "conceptual": explains ideas/concepts without heavy formalism or code.\n'
            '- "motivational": inspirational/speech content with little instruction.\n'
            '- "mixed": a genuine blend of programming and non-technical content.\n\n'
            "Respond with ONLY a JSON object: "
            '{"category": "...", "confidence": 0.0-1.0}.\n\n'
            "CONTENT:\n"
            f"{evidence[:6000]}"
        )
        raw = client.complete(prompt, system=_SYSTEM)
        parsed = _parse_llm_json(raw)
        if parsed is not None:
            logger.info(
                "classify_content: LLM -> %s (conf=%.2f)",
                parsed["category"], parsed["confidence"],
            )
            return parsed
        logger.warning(
            "classify_content: LLM response unparseable; using keyword fallback"
        )
    except Exception as exc:  # noqa: BLE001 — never break the pipeline
        logger.warning(
            "classify_content: LLM unavailable (%s); using keyword fallback", exc
        )

    result = _keyword_fallback(evidence)
    logger.info(
        "classify_content: fallback -> %s (conf=%.2f)",
        result["category"], result["confidence"],
    )
    return result
