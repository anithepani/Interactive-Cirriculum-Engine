"""Exercise contract (section 5.3.1) - union schema by type.

Producer: Aryan (M7 Exercise Generation Engine - GPT-4o primary, Qwen2.5-Coder fallback).
Consumer: Zubair (persistence), frontend (rendering), M9 evaluation.

Four exercise types share a common envelope and carry a type-specific payload:
  - mcq         : multiple choice with distractors
  - coding      : Python coding challenge with visible + hidden tests
  - debug       : buggy snippet the learner fixes
  - conceptual  : free-text graded by LLM-as-judge vs a rubric

Anti-cheat note: coding exercises are validated by a solver LLM + sandbox execution
before being exposed (E14). Test cases must pass mutation testing (E15, M8).
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, confloat


class ExerciseType(str, Enum):
    MCQ = "mcq"
    CODING = "coding"
    DEBUG = "debug"
    CONCEPTUAL = "conceptual"


class _ExerciseBase(BaseModel):
    """Common envelope fields for all exercise types."""

    id: str = Field(..., description="Exercise id")
    type: ExerciseType = Field(..., description="Discriminator")
    ts: float = Field(..., ge=0.0, description="Checkpoint timestamp (s) in the video")
    concept_id: str = Field(..., description="Concept this exercise targets")
    difficulty: int = Field(..., ge=1, le=5, description="Difficulty 1-5")
    prompt: str = Field(..., min_length=1, description="Exercise prompt shown to learner")
    context: Optional[str] = Field(
        None, description="Optional code/context snippet shown alongside the prompt"
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Generator confidence; low items surface to admin (UC-14)"
    )
    validation_passed: bool = Field(
        False,
        description="True once M8 validates the exercise is solvable/consistent",
    )


class McqPayload(BaseModel):
    """Multiple-choice question payload."""

    options: list[str] = Field(..., min_length=2, description="Answer options")
    answer_idx: int = Field(..., description="Index of the correct option")
    distractor_tags: list[str] = Field(
        default_factory=list,
        description="Tags describing why each distractor is plausible (analytics, E13)",
    )


class CodingPayload(BaseModel):
    """Python coding challenge payload (MVP language: Python)."""

    starter: str = Field(..., description="Starter code shown in Monaco editor")
    tests_visible: list[str] = Field(
        default_factory=list, description="Visible test cases shown to the learner"
    )
    tests_hidden: list[str] = Field(
        ..., min_length=1, description="Hidden test cases run in judge0"
    )
    reference_solution: str = Field(
        ..., description="Reference solution used by M8 to validate solvability"
    )
    language: Literal["python"] = Field(
        "python", description="MVP: python only; JS/TS deferred to Phase 6"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Optional constraints (time/space, signatures)"
    )


class DebugPayload(BaseModel):
    """Buggy-snippet debugging task. Learner fixes + explains the bug."""

    buggy_code: str = Field(..., description="The buggy code the learner must fix")
    tests: list[str] = Field(..., min_length=1, description="Hidden tests that must pass")
    bug_explanation: str = Field(
        ..., description="Ground-truth bug explanation (LLM-grades learner's explanation)"
    )


class ConceptualPayload(BaseModel):
    """Free-text question graded by LLM-as-judge vs a rubric + reference answer."""

    reference_answer: str = Field(..., description="Reference answer")
    rubric: list[str] = Field(..., min_length=1, description="Grading rubric items")
    min_similarity: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Embedding-similarity threshold for auto-pass"
    )


# ---- Typed envelopes (one per exercise type) ----


class McqExercise(_ExerciseBase):
    type: Literal[ExerciseType.MCQ] = ExerciseType.MCQ
    mcq: McqPayload


class CodingExercise(_ExerciseBase):
    type: Literal[ExerciseType.CODING] = ExerciseType.CODING
    coding: CodingPayload


class DebugExercise(_ExerciseBase):
    type: Literal[ExerciseType.DEBUG] = ExerciseType.DEBUG
    debug: DebugPayload


class ConceptualExercise(_ExerciseBase):
    type: Literal[ExerciseType.CONCEPTUAL] = ExerciseType.CONCEPTUAL
    conceptual: ConceptualPayload


# Discriminated union: the `type` field routes to the right payload.
Exercise = Annotated[
    Union[McqExercise, CodingExercise, DebugExercise, ConceptualExercise],
    Field(discriminator="type"),
]
