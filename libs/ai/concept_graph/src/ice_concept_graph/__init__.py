"""M5 Knowledge Graph / Concept Mapper.

Input: concepts from M4. Output: concept nodes + prerequisite/dependency edges,
mapped to a curated CS/programming concept taxonomy.

Tech: LLM-extracted relations; stored as a property graph (Postgres + adjacency,
optional Neo4j later); link to Wikidata/CS taxonomy for canonical IDs.

Paper [OPT]: Concept-map learning literature; "Open Learner Models".

Lead: Aryan. Support: Zubair (storage).
"""
from __future__ import annotations

from ice_contracts import Concept, Segment


def build_concept_graph(segments: list[Segment]) -> tuple[list[Concept], list[tuple[str, str, str]]]:
    """Return (concept_nodes, [(src_id, dst_id, relation_label), ...])."""
    raise NotImplementedError("Phase 2 deliverable")
