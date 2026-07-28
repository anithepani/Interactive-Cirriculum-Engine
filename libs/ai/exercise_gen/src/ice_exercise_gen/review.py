"""M7 Review Generation Engine.

Generates the new spaced-repetition review payload for each concept based on its category.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from ice_contracts.review import (
    ReviewPayload,
    ReviewOutputPrediction,
    ReviewFillGap,
    ReviewSpotBug,
    ReviewConceptRecall,
    ReviewTraceState,
    ReviewLegacy,
)
from ice_llm.client import LLMClient

logger = logging.getLogger(__name__)

_CATEGORY_TO_FORMAT = {
    "syntax/mechanism": ["fill_gap", "output_prediction"],
    "algorithmic complexity": ["concept_recall"],
    "loops/recursion": ["trace_state"],
    "common-mistake-prone topics": ["spot_bug"],
    "general": ["concept_recall"],
}

def _extract_json(raw: str) -> dict | None:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None

def generate_concept_reviews(concepts: list[dict], transcript_text: str) -> list[dict]:
    """Enrich each concept with review_format and review_payload."""
    llm = LLMClient()

    for concept in concepts:
        category = concept.get("category", "general")
        formats = _CATEGORY_TO_FORMAT.get(category, ["concept_recall"])
        # Deterministic simple selection if multiple formats map to a category
        review_format = formats[0]
        if category == "syntax/mechanism" and "output" in concept.get("description", "").lower():
            review_format = "output_prediction"

        # Special fallback for missing things
        if not concept.get("label"):
            continue
            
        concept["review_format"] = review_format
        
        prompt = _build_prompt(concept, review_format, transcript_text)
        raw = llm.complete(prompt, tier="high_value")
        payload_dict = _extract_json(raw)
        
        if not payload_dict:
            _fallback_legacy(concept)
            continue
            
        # Pydantic validation
        payload_dict["type"] = review_format
        try:
            if review_format == "output_prediction":
                ReviewOutputPrediction.model_validate(payload_dict)
            elif review_format == "fill_gap":
                ReviewFillGap.model_validate(payload_dict)
            elif review_format == "spot_bug":
                ReviewSpotBug.model_validate(payload_dict)
                # Note: Precomputing Judge0 is requested. If we had a local runner, we'd do it here.
                # For now we rely on the LLM's `expected_output`.
            elif review_format == "concept_recall":
                ReviewConceptRecall.model_validate(payload_dict)
            elif review_format == "trace_state":
                ReviewTraceState.model_validate(payload_dict)
            else:
                _fallback_legacy(concept)
                continue
                
            concept["review_payload"] = payload_dict
        except ValidationError as e:
            logger.warning("Failed to validate review payload for %s: %s", concept.get("id"), e)
            _fallback_legacy(concept)
            
    return concepts

def _fallback_legacy(concept: dict) -> None:
    concept["review_format"] = "legacy"
    concept["review_payload"] = {
        "type": "legacy",
        "legacy": True,
        "question": concept.get("label", ""),
        "answer": concept.get("description", "")
    }

def _build_prompt(concept: dict, review_format: str, transcript_text: str) -> str:
    base = (
        f"You are an expert programming instructor. Generate a spaced-repetition review flashcard "
        f"for the concept '{concept.get('label')}' ({concept.get('description')}).\n"
        f"Use the following transcript context to ground the code:\n{transcript_text[:2000]}\n\n"
        "Return ONLY a valid JSON object. Do not use markdown formatting.\n"
    )
    if review_format == "output_prediction":
        return base + (
            "Format: output_prediction\n"
            "Return JSON with fields:\n"
            '- "code": (string) the code snippet\n'
            '- "expected_output": (string) the exact output\n'
            '- "explanation": (string) why it works\n'
        )
    elif review_format == "fill_gap":
        return base + (
            "Format: fill_gap\n"
            "Return JSON with fields:\n"
            '- "code": (string) the code snippet with exactly one {{blank}} where a keyword/operator belongs\n'
            '- "answer": (string) the exact string to fill the gap\n'
            '- "explanation": (string) why this is the answer\n'
        )
    elif review_format == "spot_bug":
        return base + (
            "Format: spot_bug\n"
            "Return JSON with fields:\n"
            '- "code": (string) the code snippet containing exactly one bug\n'
            '- "bug_line": (int) the 1-indexed line number of the bug\n'
            '- "fixed_code": (string) the fully corrected code\n'
            '- "expected_output": (string) the output of the fixed code\n'
            '- "explanation": (string) why the bug occurs and how to fix it\n'
        )
    elif review_format == "concept_recall":
        return base + (
            "Format: concept_recall\n"
            "Return JSON with fields:\n"
            '- "question": (string) a short multiple-choice question testing the "why"\n'
            '- "options": (list of strings) exactly 4 possible answers\n'
            '- "answer_index": (int) 0-indexed position of correct answer\n'
            '- "explanation": (string) why the answer is correct\n'
        )
    elif review_format == "trace_state":
        return base + (
            "Format: trace_state\n"
            "Return JSON with fields:\n"
            '- "code": (string) a loop or recursive function\n'
            '- "initial_variables": (dict mapping string to string) the starting variable states\n'
            '- "table": (list of dicts) where each dict has "iteration" (int or str) and "variables" (dict mapping string to string)\n'
            '- "explanation": (string) summary of the trace\n'
        )
    return base
