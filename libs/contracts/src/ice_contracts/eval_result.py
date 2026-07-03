"""Evaluation result contract (section 5.3.1).

Producer: Aryan (M9 Answer Evaluation & Feedback Engine).
Consumers: Zubair (persistence), frontend (results panel), M10 adaptive controller.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, confloat


class EvalVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class EvalResult(BaseModel):
    """The verdict, score, explanation, hints, and anti-cheat signal for one attempt."""

    exercise_id: str = Field(..., description="Exercise that was attempted")
    verdict: EvalVerdict = Field(..., description="pass | fail | partial")
    score: confloat(ge=0.0, le=1.0) = Field(..., description="Normalized score 0-1")
    explanation: str = Field(..., description="Why the verdict (shown to learner)")
    hints: list[str] = Field(
        default_factory=list, description="Hints for retry / remediation"
    )
    anti_cheat_flag: bool = Field(
        False,
        description=(
            "True if CodeBLEU/AST-diff similarity to instructor's code exceeds "
            "threshold (E12 - learner copied instructor's example)"
        ),
    )
