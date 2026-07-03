"""M5 Knowledge Graph / Concept Mapper - concept node + edge extraction.

Builds a concept graph from M4 segments: deduplicates concepts, enriches them
with LLM-generated descriptions + difficulty, and extracts prerequisite/related/
part_of edges via batched LLM calls.

Lead: Aryan. Support: Zubair (storage).
"""
from __future__ import annotations

from ice_concept_graph.extractor import extract_concepts_and_edges

__all__ = ["extract_concepts_and_edges"]
