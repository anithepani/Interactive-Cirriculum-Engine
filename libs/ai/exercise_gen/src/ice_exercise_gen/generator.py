"""M7 Exercise Generation Engine - core generator.

Produces exercises of four types (mcq, coding, debug, conceptual) from
checkpoints, segments, and concepts. Each checkpoint maps to one exercise
whose type is determined by the checkpoint's ``exercise_type`` field.

Design:
  - Plain-dict I/O (consistent with M2/M4/M5/M6).
  - Each output dict is validated against ``ice_contracts.Exercise`` (the
    discriminated-union Pydantic model) and returned via ``model_dump()``
    so consumers always receive contract-compliant data.
  - Structured output is enforced via prompt instructions + ``json.loads``
    + Pydantic validation, with one retry on parse/validation failure.
  - Coding/debug exercises receive the instructor's extracted code (when
    available) to force transfer, not recall (anti-cheat E12).

Lead: Aryan. Support: Ahmed (code-context from OCR).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ice_contracts.exercise import Exercise
from ice_llm import get_client

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PROMPT_DIR = _REPO_ROOT / "prompt-library" / "exercise_gen"

_SYSTEM = (
    "You are an expert programming instructor. You MUST respond with ONLY "
    "a single valid JSON object — no markdown fences, no prose, no explanation. "
    "The JSON must conform exactly to the requested schema."
)

_VALID_TYPES = ("mcq", "coding", "debug", "conceptual")

adapter: TypeAdapter[Exercise] = TypeAdapter(Exercise)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def generate_exercises(
    checkpoints: list[dict],
    segments: list[dict],
    concepts: list[dict],
    instructor_code: list[str] | str | None = None,
) -> list[dict]:
    """Generate one exercise per checkpoint.

    Args:
        checkpoints: M6 checkpoint dicts (must contain ``id``, ``ts``,
            ``segment_id``, ``concept_id``, ``exercise_type``, ``difficulty``).
        segments: M4 segment dicts (must contain ``id``, ``title``,
            ``summary``, ``concepts``).
        concepts: M5 concept dicts.  May be a bare list ``[{id, label, ...}]``
            or a concept-graph dict ``{"concepts": [...], "edges": [...]}``.
        instructor_code: Optional code extracted from the instructor's screen
            (M3 OCR).  Passed as a list of strings (joined) or a single string.
            Used by coding/debug prompts to force a *different* context.

    Returns:
        A list of exercise dicts, each validated against ``ice_contracts.Exercise``.
    """
    client = get_client()
    concepts_list = _normalise_concepts(concepts)
    code_str = _join_instructor_code(instructor_code)

    exercises: list[dict] = []
    for cp in checkpoints:
        seg = _resolve_segment(cp, segments)
        conc = _resolve_concept(cp, concepts_list)
        etype = _get_exercise_type(cp)
        if etype not in _VALID_TYPES:
            logger.warning("Skipping checkpoint %s: unknown exercise_type %r", cp.get("id"), etype)
            continue

        prompt = _build_prompt(etype, cp, seg, conc, code_str)
        ex_dict = _generate_one(client, prompt, cp, etype, code_str)
        if ex_dict is not None:
            exercises.append(ex_dict)
        else:
            logger.error("Failed to generate exercise for checkpoint %s (type=%s)", cp.get("id"), etype)

    logger.info("generate_exercises: produced %d/%d exercises", len(exercises), len(checkpoints))
    return exercises


# --------------------------------------------------------------------------- #
# Resolution helpers
# --------------------------------------------------------------------------- #


def _resolve_segment(cp: dict, segments: list[dict]) -> dict:
    sid = str(cp.get("segment_id", ""))
    for seg in segments:
        if str(seg.get("id", "")) == sid:
            return seg
    logger.warning("Segment %s not found for checkpoint %s", sid, cp.get("id"))
    return {}


def _resolve_concept(cp: dict, concepts: list[dict]) -> dict:
    cid = str(cp.get("concept_id", ""))
    for conc in concepts:
        if str(conc.get("id", "")) == cid:
            return conc
    logger.warning("Concept %s not found for checkpoint %s", cid, cp.get("id"))
    return {}


def _normalise_concepts(concepts: list[dict] | dict) -> list[dict]:
    """Accept either a bare list of concept dicts or a graph dict with a ``concepts`` key."""
    if isinstance(concepts, dict):
        return concepts.get("concepts", [])
    return concepts


def _get_exercise_type(cp: dict) -> str:
    et = cp.get("exercise_type")
    if et is not None:
        return str(et)
    ets = cp.get("exercise_types")
    if ets and isinstance(ets, list) and len(ets) > 0:
        return str(ets[0])
    return ""


def _join_instructor_code(instructor_code: list[str] | str | None) -> str:
    if instructor_code is None:
        return ""
    if isinstance(instructor_code, list):
        return "\n\n".join(str(c) for c in instructor_code)
    return str(instructor_code)


# --------------------------------------------------------------------------- #
# Prompt building
# --------------------------------------------------------------------------- #


def _load_template(etype: str) -> str:
    path = _PROMPT_DIR / etype / "template.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_few_shot(etype: str) -> str | None:
    path = _PROMPT_DIR / etype / "few_shot.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data and isinstance(data, list) and len(data) > 0:
            ex = data[0]
            output = ex.get("output", {})
            return json.dumps(output, indent=2)
    except Exception:
        logger.warning("Could not parse few_shot for %s", etype)
    return None


def _render(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace("{{ " + key + " }}", str(value))
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def _build_prompt(etype: str, cp: dict, seg: dict, conc: dict, code_str: str) -> str:
    template = _load_template(etype)
    difficulty = cp.get("difficulty", conc.get("difficulty", 3))

    variables = {
        "concept": conc.get("label", cp.get("concept_id", "unknown")),
        "concept_description": conc.get("description", ""),
        "difficulty": difficulty,
        "segment_summary": seg.get("summary", ""),
        "segment_title": seg.get("title", ""),
        "instructor_code": code_str or "(No instructor code was extracted for this segment.)",
    }

    prompt = _render(template, variables)

    few_shot = _load_few_shot(etype)
    if few_shot:
        prompt += "\n\n## Example output\n```json\n" + few_shot + "\n```"

    prompt += "\n\nRespond with ONLY a JSON object. No markdown fences, no prose."
    return prompt


# --------------------------------------------------------------------------- #
# LLM call + parsing + validation
# --------------------------------------------------------------------------- #


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    # Strip markdown code fences if present.
    fence = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # If there's a leading/trailing non-JSON, try to find the first {...}.
    if not text.startswith("{"):
        start = text.find("{")
        if start != -1:
            text = text[start:]
    return json.loads(text)


def _build_exercise_dict(cp: dict, etype: str, payload: dict, code_str: str) -> dict:
    """Assemble the full exercise envelope from LLM payload + checkpoint metadata."""
    ex_id = "ex_" + str(cp.get("id", "unknown")) + "_" + etype
    confidence = float(payload.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    envelope = {
        "id": ex_id,
        "type": etype,
        "ts": float(cp.get("ts", 0.0)),
        "concept_id": str(cp.get("concept_id", "")),
        "difficulty": int(cp.get("difficulty", 3)),
        "prompt": payload.get("prompt", ""),
        "context": code_str if code_str else None,
        "confidence": confidence,
        "validation_passed": False,
    }

    if etype == "mcq":
        envelope["mcq"] = {
            "options": payload.get("options", []),
            "answer_idx": payload.get("answer_idx", 0),
            "distractor_tags": payload.get("distractor_tags", []),
        }
    elif etype == "coding":
        envelope["coding"] = {
            "starter": payload.get("starter", ""),
            "tests_visible": payload.get("tests_visible", []),
            "tests_hidden": payload.get("tests_hidden", []),
            "reference_solution": payload.get("reference_solution", ""),
            "language": "python",
            "constraints": payload.get("constraints", []),
        }
    elif etype == "debug":
        envelope["debug"] = {
            "buggy_code": payload.get("buggy_code", ""),
            "tests": payload.get("tests", []),
            "bug_explanation": payload.get("bug_explanation", ""),
        }
    elif etype == "conceptual":
        envelope["conceptual"] = {
            "reference_answer": payload.get("reference_answer", ""),
            "rubric": payload.get("rubric", []),
            "min_similarity": float(payload.get("min_similarity", 0.7)),
        }

    return envelope


def _validate(ex_dict: dict) -> dict | None:
    try:
        validated = adapter.validate_python(ex_dict)
        return validated.model_dump(mode="json")
    except ValidationError as exc:
        logger.warning("Validation failed for exercise %s: %s", ex_dict.get("id"), exc)
        return None


def _generate_one(client, prompt: str, cp: dict, etype: str, code_str: str) -> dict | None:
    """Call the LLM, parse JSON, validate, and return the exercise dict.

    Retries once with a repair hint if parsing or validation fails.
    """
    for attempt in range(2):
        try:
            raw = client.complete(prompt, system=_SYSTEM)
            payload = _parse_json(raw)
            ex_dict = _build_exercise_dict(cp, etype, payload, code_str)
            validated = _validate(ex_dict)
            if validated is not None:
                return validated
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Attempt %d parse/build error for %s: %s", attempt + 1, cp.get("id"), exc)

        if attempt == 0:
            # Retry with a repair hint.
            prompt = (
                prompt
                + "\n\nIMPORTANT: Your previous response was not valid JSON or did not "
                "match the schema. Please return ONLY a single JSON object with the exact "
                "fields requested. Double-check that all required fields are present."
            )

    return None
