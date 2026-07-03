"""Adaptive progression contract (section 4.2.10).

Producer: Aryan (M10 Adaptive Progression Controller - IRT 3PL MVP, DKT stretch).
Consumer: Zubair (session state, next-checkpoint selection), frontend.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, confloat


class LearnerPerformance(BaseModel):
    """A single performance observation fed into the skill model."""

    concept_id: str = Field(..., description="Concept that was tested")
    score: confloat(ge=0.0, le=1.0) = Field(..., description="Eval score 0-1")
    response_time_sec: float = Field(..., ge=0.0, description="Time to respond")
    guessed: bool = Field(False, description="Inferred guess (E13 - low confidence)")


class AdaptiveState(BaseModel):
    """The adaptive controller's recommendation for the next checkpoint."""

    session_id: str = Field(..., description="Learning session id")
    next_difficulty: int = Field(..., ge=1, le=5, description="Recommended difficulty")
    insert_remedial: bool = Field(
        False,
        description="If mastery is low, insert a simpler analog exercise (E27 soft-fail)",
    )
    skip_next: bool = Field(
        False, description="If mastery is very high, allow skipping the next checkpoint"
    )
    performance_history: list[LearnerPerformance] = Field(default_factory=list)
