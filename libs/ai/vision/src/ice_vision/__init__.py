"""M3 Visual Content Extraction.

Input: video file. Output: OCR'd code blocks (with timestamps), detected
slides, diagrams, UI regions, keyframe set + per-item confidence.
"""
from __future__ import annotations

from ice_vision.extractor import extract_visuals

__all__ = ["extract_visuals"]
