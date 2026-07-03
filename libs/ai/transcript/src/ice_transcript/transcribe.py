"""faster-whisper transcription -> canonical transcript JSON contract (§5.3.1).

Loads Whisper large-v3 on CUDA (float16) and falls back silently to CPU (int8)
when CUDA is unavailable. Maps the faster-whisper output to the exact JSON
shape the frontend and downstream AI modules consume.
"""
from __future__ import annotations

import os

from faster_whisper import WhisperModel

DEFAULT_MODEL = os.environ.get("ASR_MODEL", "large-v3")
SPEAKER_LABEL = "SPEAKER_00"  # single-speaker assumed until pyannote lands (M2)


def _load_model() -> WhisperModel:
    """Try CUDA (float16) first; fall back silently to CPU (int8)."""
    try:
        return WhisperModel(DEFAULT_MODEL, device="cuda", compute_type="float16")
    except Exception:
        # CUDA unavailable, drivers missing, or CTranslate2 built without GPU
        # support. Degrade silently to CPU per the master plan fallback strategy.
        return WhisperModel(DEFAULT_MODEL, device="cpu", compute_type="int8")


def transcribe(audio_file_path: str) -> dict:
    """Transcribe `audio_file_path` and return the canonical transcript dict.

    Contract:
        {"language": str, "confidence": float,
         "segments": [{"id": int, "start": float, "end": float, "text": str,
                       "speaker": "SPEAKER_00",
                       "words": [{"w": str, "t": float}],
                       "confidence": float}]}
    """
    model = _load_model()
    segments_iter, info = model.transcribe(audio_file_path, word_timestamps=True)

    segments_out: list[dict] = []
    for seg in segments_iter:
        words = list(seg.words or [])
        word_confidences = [w.probability for w in words if w.probability is not None]
        seg_confidence = (
            sum(word_confidences) / len(word_confidences)
            if word_confidences
            else float(info.language_probability)
        )
        segments_out.append(
            {
                "id": int(seg.id),
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
                "speaker": SPEAKER_LABEL,
                "words": [{"w": w.word, "t": float(w.start)} for w in words],
                "confidence": float(seg_confidence),
            }
        )

    return {
        "language": info.language,
        "confidence": float(info.language_probability),
        "segments": segments_out,
    }
