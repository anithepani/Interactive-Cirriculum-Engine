"""Transcript contract (section 5.3.1).

Producer: Aryan (M2 - Whisper via faster-whisper + pyannote diarization).
Consumers: all downstream modules (segmentation, exercise-gen, frontend).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, confloat


class WordToken(BaseModel):
    """A single word with its start time (seconds from video start)."""

    w: str = Field(..., description="The word text")
    t: float = Field(..., ge=0.0, description="Start time in seconds")


class TranscriptSegment(BaseModel):
    """A contiguous chunk of speech with timing, speaker, and words."""

    id: int = Field(..., description="Sequential segment id")
    start: float = Field(..., ge=0.0, description="Start time (s)")
    end: float = Field(..., ge=0.0, description="End time (s)")
    text: str = Field(..., min_length=1, description="Segment text")
    speaker: Optional[str] = Field(
        None, description="Speaker label from pyannote diarization, if any"
    )
    words: list[WordToken] = Field(
        default_factory=list, description="Word-level tokens with timestamps"
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="ASR confidence score [0,1]"
    )


class Transcript(BaseModel):
    """Full transcript for a video: segments, detected language, overall confidence."""

    language: str = Field(..., description="ISO-639-1 language code, e.g. 'en'")
    segments: list[TranscriptSegment] = Field(..., min_length=1)
    confidence: confloat(ge=0.0, le=1.0)
