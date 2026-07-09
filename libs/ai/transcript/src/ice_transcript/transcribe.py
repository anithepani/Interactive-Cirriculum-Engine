"""faster-whisper transcription -> canonical transcript JSON contract (§5.3.1).

Loads Whisper large-v3 on CUDA (float16) and falls back silently to CPU (int8)
when CUDA is unavailable. Maps the faster-whisper output to the exact JSON
shape the frontend and downstream AI modules consume.
"""
from __future__ import annotations

import os

from faster_whisper import WhisperModel

DEFAULT_MODEL = os.environ.get("ASR_MODEL", "large-v3")
DEFAULT_DEVICE = os.environ.get("ASR_DEVICE", "cuda")
DEFAULT_COMPUTE_TYPE = os.environ.get("ASR_COMPUTE_TYPE", "int8_float16")
SPEAKER_LABEL = "SPEAKER_00"  # single-speaker assumed until pyannote lands (M2)


def _load_model() -> WhisperModel:
    """Load faster-whisper honoring ASR_DEVICE/ASR_COMPUTE_TYPE env vars.

    CPU path: go straight to CPU (int8) without attempting CUDA -- avoids the
    slow load+raise cycle on CPU-only laptops. CUDA path: try float16 first,
    degrade silently to CPU int8 if CUDA/drivers are unavailable.
    """
    device = os.environ.get("ASR_DEVICE", DEFAULT_DEVICE).strip().lower()
    compute_type = os.environ.get("ASR_COMPUTE_TYPE", DEFAULT_COMPUTE_TYPE).strip().lower()
    model_name = os.environ.get("ASR_MODEL", DEFAULT_MODEL).strip()

    if device != "cuda":
        # CPU-first: never attempt CUDA (team laptops have no GPU).
        ct = compute_type if compute_type in {"int8", "int8_float16"} else "int8"
        return WhisperModel(model_name, device="cpu", compute_type=ct)

    try:
        return WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception:
        # CUDA unavailable, drivers missing, or CTranslate2 built without GPU
        # support. Degrade silently to CPU per the master plan fallback strategy.
        return WhisperModel(model_name, device="cpu", compute_type="int8")


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
