"""M6 Checkpoint Placement Controller.

Input: segments + concept graph + difficulty. Output: ordered checkpoints
[{ts, segment_id, concept_id, exercise_types[], difficulty}].

Logic: place checkpoint at topic transitions + after each "learnable" concept;
density cap (>=90s apart); avoid the final 30s; one exercise type per checkpoint
(varied across the curriculum). Cadence configurable per tenant.

Edge case E11 (multiple languages/frameworks in one video): MVP Python only -
detect non-Python and mark checkpoint as MCQ/conceptual instead of coding.

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

from ice_contracts import Checkpoint, Concept, Segment


def place_checkpoints(
    segments: list[Segment], concepts: list[Concept], min_gap_sec: float = 90.0
) -> list[Checkpoint]:
    """Produce ordered checkpoints respecting the density cap."""
    raise NotImplementedError("Phase 2 deliverable")
