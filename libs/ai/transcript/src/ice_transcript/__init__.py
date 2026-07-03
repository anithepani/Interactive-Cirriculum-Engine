"""M2 Transcript & Metadata Extraction.

Input: audio track. Output: timestamped transcript (word-level + segment-level),
detected language, speaker labels, confidence.

Tech: Whisper large-v3 via faster-whisper (CTranslate2, ~4x faster, GPU-friendly);
pyannote-audio 3.x for diarization; silero-vad for VAD.

Paper [MUST]: "Robust Speech Recognition via Large-Scale Weak Supervision"
(Whisper, Radford 2023).

Edge cases (E2, E3, E33): Whisper robust to noise; VAD skips silence; if WER high,
degrade to slide+concept-only; allow manual transcript upload; detect language
via Whisper auto; MVP supports English + code, others marked "experimental".

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

from pathlib import Path

from ice_contracts import Transcript


def transcribe(audio_path: Path, language_hint: str | None = None) -> Transcript:
    """Run ASR + diarization + VAD; return a validated Transcript contract."""
    raise NotImplementedError("Phase 1 deliverable - see libs/ai/transcript/README.md")
