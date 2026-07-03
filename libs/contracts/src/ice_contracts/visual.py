"""Visual extraction contract (section 5.3.1).

Producer: Ahmed (M3 - PaddleOCR/TrOCR + region detection + CLIP keyframe dedup).
Consumer: Aryan (fuses with transcript in M4 segmentation).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, confloat


class VisualRegionType(str, Enum):
    """Region classifier (LayoutLMv3 / DocLayNet)."""

    CODE = "code"
    SLIDE = "slide"
    DIAGRAM = "diagram"
    UI = "ui"


class VisualItem(BaseModel):
    """A detected visual element on a sampled/shot frame, with OCR text and bbox."""

    frame_idx: int = Field(..., ge=0, description="Index into the sampled frames list")
    ts: float = Field(..., ge=0.0, description="Timestamp of the frame (s)")
    type: VisualRegionType = Field(..., description="Region classifier output")
    text: str = Field(..., description="OCR'd text (code block, slide text, etc.)")
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box [x, y, w, h] normalized to [0,1]",
    )
    code_lang: Optional[str] = Field(
        None, description="Detected programming language (Python MVP) if type=code"
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="OCR confidence; low values trigger transcript-only fallback (E1)"
    )
