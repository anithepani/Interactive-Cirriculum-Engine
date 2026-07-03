"""Contract tests - validate the canonical schemas round-trip and discriminate correctly.

These run in the `contract-check` CI job. They protect the integration seam
between Aryan's AI producers and Zubair's application consumer.
"""
from __future__ import annotations

import pytest
from ice_contracts import (
    Concept,
    ConceptualExercise,
    CodingExercise,
    DebugExercise,
    EvalResult,
    EvalVerdict,
    Exercise,
    ExerciseType,
    McqExercise,
    Segment,
    Transcript,
    TranscriptSegment,
    VisualItem,
    VisualRegionType,
)


def _transcript_segment() -> TranscriptSegment:
    return TranscriptSegment(
        id=1, start=0.0, end=2.5, text="hello world", speaker="SPEAKER_00",
        words=[{"w": "hello", "t": 0.0}, {"w": "world", "t": 0.5}], confidence=0.95,
    )


def test_transcript_round_trip():
    t = Transcript(language="en", segments=[_transcript_segment()], confidence=0.95)
    raw = t.model_dump_json()
    assert Transcript.model_validate_json(raw).language == "en"


def test_visual_item_requires_bbox_of_4():
    with pytest.raises(Exception):
        VisualItem(
            frame_idx=0, ts=0.0, type=VisualRegionType.CODE, text="x=1", bbox=[0.1]
        )


def test_exercise_discriminator_routes_each_type():
    common = {
        "ts": 10.0, "concept_id": "c1", "difficulty": 3, "prompt": "p",
        "confidence": 0.9, "validation_passed": True,
    }
    mcq = Exercise.model_validate({"id": "e1", "type": "mcq", **common,
        "mcq": {"options": ["a", "b"], "answer_idx": 0, "distractor_tags": []}})
    coding = Exercise.model_validate({"id": "e2", "type": "coding", **common,
        "coding": {"starter": "", "tests_visible": [], "tests_hidden": ["assert True"],
                   "reference_solution": "x=1", "language": "python", "constraints": []}})
    debug = Exercise.model_validate({"id": "e3", "type": "debug", **common,
        "debug": {"buggy_code": "x=1", "tests": ["assert True"], "bug_explanation": "none"}})
    conceptual = Exercise.model_validate({"id": "e4", "type": "conceptual", **common,
        "conceptual": {"reference_answer": "a", "rubric": ["mentions X"], "min_similarity": 0.8}})

    assert isinstance(mcq, McqExercise)
    assert isinstance(coding, CodingExercise)
    assert isinstance(debug, DebugExercise)
    assert isinstance(conceptual, ConceptualExercise)
    assert {mcq.type, coding.type, debug.type, conceptual.type} == set(ExerciseType)


def test_eval_result_partial_verdict():
    r = EvalResult(exercise_id="e1", verdict=EvalVerdict.PARTIAL, score=0.5,
                   explanation="half right", hints=["check X"], anti_cheat_flag=False)
    assert r.score == 0.5


def test_concept_difficulty_bounds():
    with pytest.raises(Exception):
        Concept(id="c", label="l", description="d", difficulty=6)


def test_segment_structuredness_bounds():
    with pytest.raises(Exception):
        Segment(id="s", start=0.0, end=1.0, title="t", summary="x", structuredness=1.5)
