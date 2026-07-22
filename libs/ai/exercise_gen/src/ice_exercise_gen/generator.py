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

# Safety-net technicality probe (mirrors M6's placer heuristic). Used to
# remap coding/debug exercises to mcq/conceptual when a checkpoint's concept
# is non-technical (e.g. a motivational speech). M6 already filters at the
# source; this guards against stale or externally-produced checkpoints.
_TECH_KEYWORDS = (
    "python", "javascript", "typescript", "java", "c++", "c#",
    "code", "coding", "programming", "programmer", "function", "method",
    "variable", "class", "object", "oop", "inheritance", "polymorphism",
    "array", "linked list", "hashmap", "dictionary", "tuple", "recursion",
    "algorithm", "data structure", "compiler", "runtime", "syntax",
    "exception", "debug", "debugging", "api", "endpoint", "database", "sql",
    "framework", "library", "import ", "module", "package", "react", "node",
    "django", "flask", "fastapi", "html", "css", "frontend", "backend",
    "docker", "kubernetes", "git ", "github", "loop", "iteration", "boolean",
    "integer", "string",
)


def _is_technical(seg: dict, conc: dict) -> bool:
    """Heuristic probe: does this segment/concept discuss programming?"""
    parts: list[str] = []
    for key in ("title", "summary"):
        val = seg.get(key)
        if val:
            parts.append(str(val).lower())
    seg_concepts = seg.get("concepts") or []
    if isinstance(seg_concepts, list):
        parts.extend(str(c).lower() for c in seg_concepts)
    for key in ("label", "description"):
        val = conc.get(key)
        if val:
            parts.append(str(val).lower())
    haystack = " ".join(parts).strip()
    if not haystack:
        return False
    return any(kw in haystack for kw in _TECH_KEYWORDS)


def _remap_non_technical(etype: str, seg: dict, conc: dict) -> str:
    """Drop coding/debug for non-technical content; fall back to mcq/conceptual."""
    if etype in ("coding", "debug") and not _is_technical(seg, conc):
        remapped = "mcq" if etype == "coding" else "conceptual"
        logger.info(
            "Remapping non-technical %r exercise -> %r (segment=%r concept=%r)",
            etype, remapped, seg.get("id"), conc.get("id"),
        )
        return remapped
    return etype

adapter: TypeAdapter[Exercise] = TypeAdapter(Exercise)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def generate_exercises(
    checkpoints: list[dict],
    segments: list[dict],
    concepts: list[dict],
    instructor_code: list[str] | str | None = None,
    segment_texts: dict[Any, str] | list[str] | None = None,
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
        segment_texts: Optional real transcript text per segment (Phase 4
            grounding hardening). Either a mapping ``{segment_id: text}`` or a
            list aligned to ``segments`` by index. When provided, the actual
            spoken transcript for a checkpoint's segment is injected into the
            prompt so exercises are grounded in what was really said (not just
            the LLM summary). Safe fallback: when absent/empty the generator
            falls back to the segment summary exactly as before.

    Returns:
        A list of exercise dicts, each validated against ``ice_contracts.Exercise``.
    """
    client = get_client()
    concepts_list = _normalise_concepts(concepts)
    code_str = _join_instructor_code(instructor_code)
    text_map = _normalise_segment_texts(segment_texts, segments)

    exercises: list[dict] = []
    for cp in checkpoints:
        seg = _resolve_segment(cp, segments)
        conc = _resolve_concept(cp, concepts_list)
        etype = _get_exercise_type(cp)
        etype = _remap_non_technical(etype, seg, conc)
        if etype not in _VALID_TYPES:
            logger.warning("Skipping checkpoint %s: unknown exercise_type %r", cp.get("id"), etype)
            continue

        # Phase 4: resolve the real transcript text for this checkpoint's
        # segment (falls back to the summary inside _build_prompt when empty).
        seg_transcript = _lookup_segment_text(cp, seg, text_map)

        prompt = _build_prompt(etype, cp, seg, conc, code_str, seg_transcript)
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


def _normalise_segment_texts(
    segment_texts: dict[Any, str] | list[str] | None, segments: list[dict]
) -> dict[str, str]:
    """Normalise the per-segment transcript text into a ``{segment_id: text}`` map.

    Accepts either a mapping keyed by segment id, or a list aligned to
    ``segments`` by index (in which case we key it by each segment's ``id``).
    Returns an empty dict when nothing is supplied so callers fall back to the
    summary (backward compatible).
    """
    if not segment_texts:
        return {}
    if isinstance(segment_texts, dict):
        return {str(k): str(v) for k, v in segment_texts.items() if v}
    # List aligned to ``segments`` by index.
    text_map: dict[str, str] = {}
    for idx, txt in enumerate(segment_texts):
        if idx < len(segments):
            sid = str(segments[idx].get("id", idx))
            if txt:
                text_map[sid] = str(txt)
    return text_map


def _lookup_segment_text(cp: dict, seg: dict, text_map: dict[str, str]) -> str:
    """Return the real transcript text for a checkpoint's segment, or "".

    Tries the checkpoint's ``segment_id`` first, then the resolved segment's
    own ``id`` (they should match, but this is defensive against slug/int
    mismatches). Empty string when no grounded text is available.
    """
    for key in (cp.get("segment_id"), seg.get("id")):
        if key is None:
            continue
        txt = text_map.get(str(key))
        if txt and str(txt).strip():
            return str(txt)
    return ""


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


def _build_prompt(
    etype: str,
    cp: dict,
    seg: dict,
    conc: dict,
    code_str: str,
    segment_transcript_text: str = "",
) -> str:
    template = _load_template(etype)
    difficulty = cp.get("difficulty", conc.get("difficulty", 3))

    # ``segment_text`` is the grounding excerpt injected into the prompt so the
    # LLM bases the question on the actual video content. Phase 4: prefer the
    # REAL transcript text for this segment (what was actually said) when it is
    # available; only fall back to summary/other fields when it is not, so we
    # never regress older callers that don't pass transcript text.
    segment_text = (
        (segment_transcript_text or "").strip()
        or seg.get("text")
        or seg.get("transcript")
        or seg.get("summary")
        or "(No excerpt available for this segment.)"
    )

    is_tech = etype in ("coding", "debug")
    has_code = bool((code_str or "").strip())

    variables = {
        "concept": conc.get("label", cp.get("concept_id", "unknown")),
        "concept_description": conc.get("description", ""),
        "difficulty": difficulty,
        "segment_summary": seg.get("summary", ""),
        "segment_title": seg.get("title", ""),
        "segment_text": segment_text,
        "segment_transcript": segment_text,
        "instructor_code": code_str or "(No instructor code was extracted for this segment.)",
    }

    prompt = _render(template, variables)

    few_shot = _load_few_shot(etype)
    if few_shot:
        prompt += "\n\n## Example output\n```json\n" + few_shot + "\n```"

    # Phase 4 grounding hardening: force the model to stay strictly within the
    # provided transcript + OCR code and forbid inventing facts, APIs, or code
    # that do not appear in the lesson material. Injected for every type.
    grounding = (
        "\n\n## Grounding rules (STRICT)\n"
        "- Base the exercise ONLY on the TRANSCRIPT and (when present) the "
        "INSTRUCTOR CODE below. These are the ground truth for this segment.\n"
        "- Do NOT invent facts, functions, APIs, libraries, values, or code "
        "that are not present in or directly implied by the transcript/OCR "
        "code. Do not hallucinate.\n"
        "- If a detail is not supported by the provided material, omit it "
        "rather than guessing.\n"
        "### TRANSCRIPT (actual spoken content for this segment)\n"
        f"{segment_text}\n"
    )
    if is_tech and has_code:
        # Technical types (coding/debug): attach the instructor's on-screen
        # code (M3 OCR) as explicit grounding so the exercise is anchored to
        # the real lesson code, not a plausible invention.
        grounding += (
            "### INSTRUCTOR CODE (on-screen OCR — ground the code in THIS)\n"
            "```\n" + code_str.strip() + "\n```\n"
            "- For this coding/debug task, the code you produce MUST be "
            "consistent with the instructor code above (same language, style, "
            "and problem domain).\n"
        )
    prompt += grounding

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


def _derive_context(etype: str, payload: dict, code_str: str) -> str | None:
    """Decide the supporting code snippet shown alongside the exercise.

    Issue 2: previously ``context`` was blindly set to the OCR-extracted
    ``code_str`` for EVERY exercise, so irrelevant IDE/terminal dumps appeared
    under a "CODE SNIPPET" box — even for MCQ/conceptual questions. Rules:

    - coding / debug (technical, Phase 4): attach the instructor's OCR code as
      grounding context so the learner sees the real lesson code the exercise
      is anchored to — UNLESS the same snippet is already reproduced in the
      editor (starter/buggy_code) or the prompt, in which case a second copy
      would only clutter the UI.
    - mcq / conceptual: only attach the OCR code when it is substantial and not
      already reproduced in the prompt (some questions quote the snippet inline).
    - never attach empty/whitespace-only or trivially short OCR fragments.
    """
    code = (code_str or "").strip()
    if not code or len(code) < 12:
        return None

    prompt = str(payload.get("prompt", "") or "")
    # If the prompt already contains the snippet, don't duplicate it.
    if code[:40] in prompt:
        return None

    if etype in ("debug", "coding"):
        # Phase 4: technical types attach the OCR instructor code as grounding.
        # Skip only when the editor content (starter/buggy_code) already
        # contains this exact snippet, so we never show a redundant copy.
        editor_code = str(
            payload.get("starter", "") or payload.get("buggy_code", "") or ""
        )
        if code[:40] and code[:40] in editor_code:
            return None
        return code

    return code


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
        "context": _derive_context(etype, payload, code_str),
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
        fixed = payload.get("fixed_code", "") or ""
        envelope["debug"] = {
            "buggy_code": payload.get("buggy_code", ""),
            "tests": payload.get("tests", []),
            "bug_explanation": payload.get("bug_explanation", ""),
            # Corrected code (Issue 4): the reference answer shown in review.
            "fixed_code": fixed or None,
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
