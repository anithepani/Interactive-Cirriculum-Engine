"""M4 Lesson Structure Analyzer - topic segmentation via embedding similarity.

Splits a transcript into ordered topic segments using sentence embeddings,
cosine similarity boundary detection, BERTopic labeling, and LLM-generated
titles + summaries.

Lead: Aryan. Support: Ahmed (visual fusion).
"""
from __future__ import annotations

from ice_segmentation.segmenter import segment_transcript

__all__ = ["segment_transcript"]
