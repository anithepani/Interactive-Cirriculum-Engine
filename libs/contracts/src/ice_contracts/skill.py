"""Skill model contract (section 4.2.11).

Producer: Zubair (M11 Learner Profile & Progress Tracker), with Aryan's input.
Consumer: M10 adaptive controller, frontend progress dashboard.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, confloat


class SkillModel(BaseModel):
    """Per-concept mastery estimates for a learner."""

    learner_id: str = Field(..., description="User id")
    curriculum_id: str = Field(..., description="Curriculum the skill model applies to")
    mastery: dict[str, confloat(ge=0.0, le=1.0)] = Field(
        default_factory=dict,
        description="Map of concept_id -> mastery estimate [0,1] (IRT theta-derived)",
    )
    weak_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts below the mastery threshold (surfaced on dashboard)",
    )
