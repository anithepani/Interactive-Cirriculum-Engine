"""M2 Transcript & Metadata Extraction.

Phase-0 implementation: faster-whisper (large-v3) with CUDA->CPU fallback,
emitting the canonical transcript JSON contract (§5.3.1). pyannote diarization
and silero VAD land in a later phase; single-speaker is assumed for now.

Paper [MUST]: "Robust Speech Recognition via Large-Scale Weak Supervision"
(Whisper, Radford 2023).

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

from ice_transcript.transcribe import transcribe

__all__ = ["transcribe"]
