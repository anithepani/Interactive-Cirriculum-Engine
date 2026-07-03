"""AI service API request/response shapes (section 5.3.2).

Aryan owns these endpoints' AI semantics; Zubair consumes them. The OpenAPI 3.1
spec in docs/api/openapi.yaml is the canonical HTTP description; these Pydantic
models are the in-code shapes both sides import.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from ice_contracts.adaptive import AdaptiveState
from ice_contracts.curriculum import Curriculum
from ice_contracts.eval_result import EvalResult
from ice_contracts.exercise import Exercise
from ice_contracts.segment import Segment
from ice_contracts.visual import VisualItem

from pydantic import BaseModel, Field


# ---- POST /ai/curriculum/generate (async) ----


class CurriculumGenerateRequest(BaseModel):
    video_ref: str = Field(
        ..., description="YouTube URL or uploaded object key (yt-dlp / file upload)"
    )
    tenant_id: UUID = Field(..., description="Owning tenant (quota + RLS)")


class CurriculumGenerateResponse(BaseModel):
    curriculum_id: UUID
    status: str = Field(default="queued", description="Initial pipeline status")


# ---- GET /ai/curriculum/{id} ----


class CurriculumGetResponse(Curriculum):
    """Full curriculum JSON (inherits all Curriculum fields)."""


# ---- POST /ai/evaluate ----


class EvaluateRequest(BaseModel):
    exercise_id: str
    response: dict = Field(
        ...,
        description=(
            "Type-specific learner response: "
            "{option_idx} for mcq, {code} for coding, {fixed_code, explanation} "
            "for debug, {text} for conceptual"
        ),
    )


class EvaluateResponse(EvalResult):
    """Eval result (inherits EvalResult fields)."""


# ---- POST /ai/regenerate ----


class RegenerateRequest(BaseModel):
    exercise_id: str
    constraints: Optional[dict] = Field(
        None,
        description="Optional constraints, e.g. {difficulty: 3, new_context: true}",
    )


class RegenerateResponse(Exercise):
    """A fresh exercise variant (same concept, different context)."""


# ---- GET /ai/adaptive/{session_id} ----


class AdaptiveStateResponse(AdaptiveState):
    """Next checkpoint + difficulty recommendation (inherits AdaptiveState)."""


# ---- (Internal) POST /vision/extract ----


class VisionExtractRequest(BaseModel):
    video_ref: str
    tenant_id: UUID


class VisionExtractResponse(BaseModel):
    items: list[VisualItem] = Field(
        default_factory=list, description="Detected visual items (M3 output)"
    )


# ---- (Internal) POST /nlp/segment ----


class NlpSegmentRequest(BaseModel):
    """Fuses transcript + visuals into segments (Aryan's M4 input)."""

    transcript_json: dict = Field(..., description="Serialized Transcript")
    visual_items: list[VisualItem] = Field(default_factory=list)
    language_hint: Optional[str] = None


class NlpSegmentResponse(BaseModel):
    segments: list[Segment] = Field(default_factory=list)
