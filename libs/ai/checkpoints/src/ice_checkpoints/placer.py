"""M6 Checkpoint Placement Controller.

Places checkpoints at the start of each segment, enforcing a density cap
(min_gap_sec apart), avoiding the final 30s, rotating exercise types, and
assigning the best-matched concept from the M5 concept graph.

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

import re

_EXERCISE_TYPES = ["mcq", "coding", "debug", "conceptual"]
_AVOID_FINAL_SEC = 30.0
_DEFAULT_DIFFICULTY = 3
_FALLBACK_CONCEPT_ID = "general"


def _slugify(label: str) -> str:
    """Convert a concept label to a stable dot-separated id (mirrors M5)."""
    cleaned = re.sub(r"[^a-z0-9 ]+", "", label.lower()).strip()
    if not cleaned:
        cleaned = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
    parts = [p for p in cleaned.split() if p]
    return ".".join(parts) if parts else "concept"


def _pick_concept_id(
    seg_concepts: list[str], graph_concept_ids: set[str], fallback: str
) -> str:
    """Pick the first segment concept that exists in the graph; else fallback."""
    for c in seg_concepts:
        cid = _slugify(c)
        if cid in graph_concept_ids:
            return cid
    return fallback


def place_checkpoints(
    segments: list[dict], concept_graph: dict, min_gap_sec: float = 90.0
) -> list[dict]:
    """Place checkpoints at segment starts subject to density + final-30s rules.

    Args:
        segments: M4 segment dicts, each with ``id``, ``start``, ``end``,
            and ``concepts`` (list[str]).
        concept_graph: M5 output dict with ``concepts`` (list of node dicts
            each having ``id``) and ``edges``.
        min_gap_sec: Minimum seconds between consecutive checkpoints.
            Defaults to 90 (production); pass a smaller value for short
            demo videos.

    Returns:
        A list of checkpoint dicts, each with keys: ``id`` (str, e.g.
        "cp_1"), ``ts`` (float), ``segment_id`` (str), ``concept_id`` (str),
        ``exercise_type`` (str), ``difficulty`` (int 1-5).
    """
    if not segments:
        return []

    # Collect valid concept ids from the graph.
    graph_concept_ids: set[str] = set()
    fallback_concept_id = _FALLBACK_CONCEPT_ID
    for node in concept_graph.get("concepts", []):
        nid = node.get("id")
        if nid:
            graph_concept_ids.add(nid)
            fallback_concept_id = nid  # last one wins as fallback

    video_duration = max(seg["end"] for seg in segments)
    avoid_zone_start = video_duration - _AVOID_FINAL_SEC

    checkpoints: list[dict] = []
    last_ts = -min_gap_sec  # so the first segment always passes

    for seg in segments:
        ts = float(seg.get("start", 0.0))

        # Density cap: skip if too close to the previous checkpoint.
        if ts - last_ts < min_gap_sec:
            continue

        # Avoid the final 30 seconds of the video.
        if ts > avoid_zone_start:
            continue

        seg_id = str(seg.get("id", ""))
        seg_concepts = seg.get("concepts", [])
        concept_id = _pick_concept_id(seg_concepts, graph_concept_ids, fallback_concept_id)

        idx = len(checkpoints)
        checkpoints.append(
            {
                "id": f"cp_{idx + 1}",
                "ts": ts,
                "segment_id": seg_id,
                "concept_id": concept_id,
                "exercise_type": _EXERCISE_TYPES[idx % len(_EXERCISE_TYPES)],
                "difficulty": _DEFAULT_DIFFICULTY,
            }
        )
        last_ts = ts

    return checkpoints
