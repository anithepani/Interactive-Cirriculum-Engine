"""Segment / topic contract (section 5.3.1).

Producer: Aryan (M4 Lesson Structure Analyzer - hybrid TextTiling + BERTopic + LLM refine).
Consumer: Zubair (persistence), M6 checkpoint placement, frontend timeline.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, confloat


class Segment(BaseModel):
    """An ordered topic segment within the lesson."""

    id: str = Field(..., description="Segment id")
    start: float = Field(..., ge=0.0, description="Start time (s)")
    end: float = Field(..., ge=0.0, description="End time (s)")
    title: str = Field(..., min_length=1, description="LLM-generated topic title")
    summary: str = Field(..., description="LLM-generated short summary")
    concepts: list[str] = Field(
        default_factory=list, description="Concept ids covered in this segment"
    )
    source_frames: list[int] = Field(
        default_factory=list, description="Frame indices that produced this segment"
    )
    structuredness: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="How structured the segment is (E4 - low values warn the user)",
    )
