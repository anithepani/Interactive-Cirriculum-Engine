"""M6 Checkpoint Placement Controller.

Places checkpoints at segment starts, enforcing a density cap, avoiding the
final 30s, rotating exercise types, and linking the best-matched concept.

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

from ice_checkpoints.classifier import classify_content
from ice_checkpoints.placer import place_checkpoints

__all__ = ["classify_content", "place_checkpoints"]
