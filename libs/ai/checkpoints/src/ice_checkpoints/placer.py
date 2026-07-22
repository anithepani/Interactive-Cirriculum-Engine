"""M6 Checkpoint Placement Controller.

Places checkpoints at the *end* of each segment so the learner is tested
after consuming that segment's content (active recall), enforcing a density
cap (min_gap_sec apart), a minimum startup delay (min_start_sec), avoiding
the final ``avoid_final_sec`` of the video (with an exemption for the final
segment), rotating exercise types, and assigning the best-matched concept
from the M5 concept graph.

Exercise-type rotation is content-aware (Phase 4, no fixed sequence): segments
whose concept/text look technical (programming) prioritise ``coding``/``debug``
(alternating, with an ``mcq`` break-up so three code tasks never fire in a
row); non-technical segments use only ``["mcq", "conceptual"]`` so
motivational/speech content never produces coding/debug exercises. No exercise
type repeats more than twice consecutively. See ``_choose_exercise_type``.

Lead: Aryan. Support: Zubair.
"""
from __future__ import annotations

import re

_TECH_TYPES = ["mcq", "coding", "debug", "conceptual"]
_NONTECH_TYPES = ["mcq", "conceptual"]
# Backwards-compatible alias for any external caller reading the module
# constant directly.
_EXERCISE_TYPES = _TECH_TYPES
_DEFAULT_AVOID_FINAL_SEC = 30.0
_AVOID_FINAL_SEC = _DEFAULT_AVOID_FINAL_SEC  # backwards-compat alias
_DEFAULT_DIFFICULTY = 3
_FALLBACK_CONCEPT_ID = "general"

# Phase 4: learner-selected difficulty → pipeline tuning. Easy spreads
# checkpoints further apart with gentler exercises; Hard tightens the spacing
# and raises exercise difficulty. Unknown/None values fall back to "medium".
_DIFFICULTY_MIN_GAP_SEC = {"easy": 150.0, "medium": 90.0, "hard": 60.0}
_DIFFICULTY_NUMERIC = {"easy": 2, "medium": 3, "hard": 4}


def _difficulty_params(difficulty: str | None) -> tuple[float, int]:
    """Map a difficulty string to (min_gap_sec, numeric_difficulty).

    Defaults to the "medium" tuning for unknown/None inputs so callers that
    omit difficulty (and pre-migration curricula) behave exactly as before.
    """
    key = (difficulty or "medium").strip().lower()
    if key not in _DIFFICULTY_MIN_GAP_SEC:
        key = "medium"
    return _DIFFICULTY_MIN_GAP_SEC[key], _DIFFICULTY_NUMERIC[key]

# Keywords that strongly indicate a programming/technical segment. Used to
# decide whether ``coding``/``debug`` exercise types are appropriate. Kept
# deliberately biased toward unambiguous programming terms to avoid flagging
# ordinary speech as technical.
_TECH_KEYWORDS = (
    "python", "javascript", "typescript", "java ", "java.", "java,",
    " c++", " c#", " golang", " rust ", " ruby ", " kotlin",
    "code", "coding", "program", "programming", "programmer",
    "function", "functional", "method", "parameter", "argument",
    "variable", "assign", "class", "object", "object-oriented", "oop",
    "inheritance", "polymorphism", "encapsulation",
    "array", "linked list", "hashmap", "hash map", "dictionary",
    "tuple", "recursion", "recursive", "algorithm", "data structure",
    "compiler", "runtime", "syntax", "exception", "stack trace",
    "debug", "debugging", "bug ", " breakpoint",
    "api", "endpoint", "rest", "graphql", "grpc",
    "database", "sql", "query", "orm",
    "framework", "library", "import ", "module", "package",
    "react", "next.js", "vue", "angular", "svelte",
    "node", "express", "django", "flask", "fastapi",
    "html", "css", "dom", "frontend", "backend", "fullstack",
    "devops", "docker", "kubernetes", "ci/cd", "git ", "github",
    "loop", "for loop", "while loop", "iteration", "iterate",
    "boolean", "integer", "float ", "string",
)


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


_MAX_SAME_TYPE_STREAK = 2


def _choose_exercise_type(is_tech: bool, recent: list[str]) -> str:
    """Pick a content-aware exercise type for the next checkpoint.

    Content-aware rotation (Phase 4, no fixed sequence):
      - Technical segments prioritise ``coding``/``debug`` (alternating), and
        fall back to ``mcq`` when the last two checkpoints were both code-heavy
        so a learner is never hit with three coding/debug tasks in a row.
      - Non-technical segments use only ``mcq``/``conceptual``.
      - No exercise type may repeat more than ``_MAX_SAME_TYPE_STREAK`` (2)
        times consecutively; if the natural choice would break that rule the
        next candidate in the bucket is used instead.

    Args:
        is_tech: Whether the segment/concept looks technical (M6 heuristic).
        recent: The exercise types already assigned, most-recent last. Only
            the tail is inspected.

    Returns:
        One of ``mcq``/``coding``/``debug``/``conceptual``.
    """
    bucket = _TECH_TYPES if is_tech else _NONTECH_TYPES
    last = recent[-1] if recent else None
    prev = recent[-2] if len(recent) >= 2 else None
    streak = 0
    if last is not None:
        for t in reversed(recent):
            if t == last:
                streak += 1
            else:
                break

    # Build a priority-ordered candidate list for this segment kind.
    if is_tech:
        code_types = ["coding", "debug"]
        # Alternate code types: if the last one was a code type, prefer the
        # *other* code type first for variety.
        if last == "coding":
            code_types = ["debug", "coding"]
        elif last == "debug":
            code_types = ["coding", "debug"]
        # If the last two were both code-heavy, break it up with an mcq first.
        last_two_code = last in ("coding", "debug") and prev in ("coding", "debug")
        if last_two_code:
            candidates = ["mcq", *code_types, "conceptual"]
        else:
            candidates = [*code_types, "mcq", "conceptual"]
    else:
        # Non-technical: alternate mcq/conceptual for variety.
        candidates = ["conceptual", "mcq"] if last == "mcq" else ["mcq", "conceptual"]

    # Enforce the no-more-than-twice-in-a-row rule: skip any candidate that
    # would extend an existing streak of length >= _MAX_SAME_TYPE_STREAK.
    for cand in candidates:
        if cand == last and streak >= _MAX_SAME_TYPE_STREAK:
            continue
        if cand in bucket:
            return cand
    # Fallback: first bucket entry that does not violate the streak rule, else
    # the first bucket entry (guarantees a valid return).
    for cand in bucket:
        if not (cand == last and streak >= _MAX_SAME_TYPE_STREAK):
            return cand
    return bucket[0]


def _is_technical(seg: dict, concept_node: dict | None) -> bool:
    """Heuristic: does this segment/concept discuss programming?

    Checks the segment title/summary/concepts and the resolved concept node's
    label/description for programming keywords. Returns False when there is no
    textual signal at all (treated as non-technical -> safe fallback).
    """
    parts: list[str] = []
    for key in ("title", "summary"):
        val = seg.get(key)
        if val:
            parts.append(str(val).lower())
    seg_concepts = seg.get("concepts") or []
    if isinstance(seg_concepts, list):
        parts.extend(str(c).lower() for c in seg_concepts)
    if concept_node:
        for key in ("label", "description"):
            val = concept_node.get(key)
            if val:
                parts.append(str(val).lower())
    haystack = " ".join(parts)
    if not haystack.strip():
        return False
    return any(kw in haystack for kw in _TECH_KEYWORDS)


def place_checkpoints(
    segments: list[dict],
    concept_graph: dict,
    min_gap_sec: float = 90.0,
    min_start_sec: float = 60.0,
    avoid_final_sec: float = _DEFAULT_AVOID_FINAL_SEC,
    difficulty: str | None = None,
) -> list[dict]:
    """Place checkpoints at segment *ends* subject to placement rules.

    A checkpoint fires at ``seg["end"]`` (the natural topic-transition
    boundary) so the learner has finished watching that segment before being
    tested on it. The checkpoint's concepts/segment_id still reference the
    segment that just finished (the segment whose end was reached).

    Args:
        segments: M4 segment dicts, each with ``id``, ``start``, ``end``,
            and ``concepts`` (list[str]).
        concept_graph: M5 output dict with ``concepts`` (list of node dicts
            each having ``id``) and ``edges``.
        min_gap_sec: Minimum seconds between consecutive checkpoints.
            Defaults to 90 (production); pass a smaller value for short
            demo videos. When ``difficulty`` is supplied it overrides this
            with the difficulty-mapped gap (easy=150, medium=90, hard=60).
        min_start_sec: Minimum seconds before the first checkpoint may
            appear. Checkpoints with ``ts < min_start_sec`` are skipped so
            learners ingest content before being tested. Defaults to 60
            (production); pass 0 for short demo videos.
            Kept separate from ``min_gap_sec`` so demo gap overrides do not
            affect the startup-delay floor.
        avoid_final_sec: Avoid placing checkpoints in the final N seconds of
            the video, *except* for the final segment (whose end == video
            duration) which is always eligible. Non-final checkpoints are
            never clamped backward (clamping would re-trigger the
            pre-content timing bug for short trailing segments).
        difficulty: Optional learner-selected difficulty ("easy" | "medium" |
            "hard", Phase 4). When provided it tunes checkpoint density
            (``min_gap_sec``) and the numeric ``difficulty`` stamped on each
            checkpoint (easy=2, medium=3, hard=4). ``None``/unknown falls back
            to medium so existing callers are unaffected.

    Returns:
        A list of checkpoint dicts, each with keys: ``id`` (str, e.g.
        "cp_1"), ``ts`` (float, the segment end), ``segment_id`` (str),
        ``concept_id`` (str), ``exercise_type`` (str), ``difficulty``
        (int 1-5).
    """
    if not segments:
        return []

    # Phase 4: derive difficulty-tuned params. When ``difficulty`` is given it
    # overrides ``min_gap_sec`` and sets the per-checkpoint numeric difficulty;
    # when omitted we keep the caller-supplied ``min_gap_sec`` and the legacy
    # default numeric difficulty (zero-regression).
    if difficulty is not None:
        min_gap_sec, numeric_difficulty = _difficulty_params(difficulty)
    else:
        numeric_difficulty = _DEFAULT_DIFFICULTY

    # Index concept nodes by id for technicality lookups.
    graph_concept_ids: set[str] = set()
    graph_concepts_by_id: dict[str, dict] = {}
    fallback_concept_id = _FALLBACK_CONCEPT_ID
    for node in concept_graph.get("concepts", []):
        nid = node.get("id")
        if not nid:
            continue
        graph_concept_ids.add(nid)
        graph_concepts_by_id[nid] = node
        fallback_concept_id = nid  # last one wins as fallback

    video_duration = max(seg["end"] for seg in segments)
    avoid_zone_start = video_duration - avoid_final_sec

    checkpoints: list[dict] = []
    last_ts = -min_gap_sec  # so the first eligible segment always passes
    recent_types: list[str] = []  # assigned types, most-recent last

    for seg in segments:
        # Checkpoint fires at the segment END: the learner has finished the
        # segment's content before being tested on it. Falls back to start
        # only for malformed segments missing an end.
        ts = float(seg.get("end", seg.get("start", 0.0)))

        # Minimum startup delay: skip checkpoints too early in the video so
        # learners watch content before being tested (@0s bug fix).
        if ts < min_start_sec:
            continue

        # Density cap: skip if too close to the previous checkpoint.
        if ts - last_ts < min_gap_sec:
            continue

        # Avoid the final N seconds — unless this is the final segment
        # itself (its end == video_duration, which is the only checkpoint
        # the learner sees for the closing content). Non-final checkpoints
        # are dropped rather than clamped (clamping backward would fire
        # before the segment's content is fully watched).
        is_final_segment = ts >= video_duration - 1e-6
        if not is_final_segment and ts > avoid_zone_start:
            continue

        seg_id = str(seg.get("id", ""))
        seg_concepts = seg.get("concepts", [])
        concept_id = _pick_concept_id(seg_concepts, graph_concept_ids, fallback_concept_id)
        concept_node = graph_concepts_by_id.get(concept_id)

        # Content-aware exercise-type rotation (Phase 4): technical segments
        # prioritise coding/debug, non-technical segments only get mcq/
        # conceptual, and no type repeats more than twice in a row. Non-
        # technical segments never get coding/debug exercises (bug #7).
        exercise_type = _choose_exercise_type(
            _is_technical(seg, concept_node), recent_types
        )
        recent_types.append(exercise_type)

        idx = len(checkpoints)
        checkpoints.append(
            {
                "id": f"cp_{idx + 1}",
                "ts": ts,
                "segment_id": seg_id,
                "concept_id": concept_id,
                "exercise_type": exercise_type,
                "difficulty": numeric_difficulty,
            }
        )
        last_ts = ts

    return checkpoints
