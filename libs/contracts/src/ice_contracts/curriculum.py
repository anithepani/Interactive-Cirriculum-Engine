"""Curriculum contract - the top-level artifact the pipeline persists.

Producer: Aryan (the full async pipeline, M2-M8).
Consumer: Zubair (persistence in `curricula` table, REST API), frontend (player).

Status transitions: queued -> processing -> ready | failed.
A curriculum is only `ready` once every exercise has `validation_passed=True`.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CurriculumStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Curriculum(BaseModel):
    """The full interactive curriculum for one video."""

    id: UUID = Field(..., description="curriculum_id (also the API path param)")
    tenant_id: UUID = Field(..., description="Owning tenant (RLS isolation)")
    video_ref: str = Field(..., description="YouTube URL or uploaded object key")
    title: str = Field(..., description="Auto-derived or video title")
    status: CurriculumStatus = Field(..., description="Pipeline status")
    language: str = Field(default="en", description="Detected language")
    duration_sec: float = Field(..., gt=0.0, description="Video duration (s)")
    segments: list = Field(default_factory=list, description="List[Segment] (M4)")
    concepts: list = Field(default_factory=list, description="List[Concept] (M5)")
    checkpoints: list = Field(default_factory=list, description="List[Checkpoint] (M6)")
    exercises: list = Field(default_factory=list, description="List[Exercise] (M7)")
    created_at: datetime = Field(..., description="Ingestion start")
    updated_at: datetime = Field(..., description="Last pipeline update")
    completed_at: Optional[datetime] = Field(
        None, description="Set when status reaches READY"
    )
    failure_reason: Optional[str] = Field(
        None, description="Set when status is FAILED (e.g. ASR WER too high)"
    )
