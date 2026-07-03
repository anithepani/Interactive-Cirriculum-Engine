"""Checkpoint contract (section 4.2.6).

Producer: Aryan (M6 Checkpoint Placement Controller).
Consumer: Zubair (persistence), frontend (scrubber markers).

Placement logic: checkpoints land at topic transitions + after each "learnable"
concept; density cap (>=90s apart); avoid the final 30s; one exercise type per
checkpoint, varied across the curriculum.
"""
from __future__ import annotations

from ice_contracts.exercise import ExerciseType

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """A point in the video where the learner is interrupted with an exercise."""

    ts: float = Field(..., ge=0.0, description="Checkpoint timestamp (s)")
    segment_id: str = Field(..., description="Segment this checkpoint belongs to")
    concept_id: str = Field(..., description="Concept tested at this checkpoint")
    exercise_types: list[ExerciseType] = Field(
        ..., min_length=1, description="Candidate exercise types for this checkpoint"
    )
    difficulty: int = Field(..., ge=1, le=5, description="Initial difficulty 1-5")
