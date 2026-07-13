"""Async ORM persistence for the AI pipeline (worker side).

Maps the dict outputs of the AI libs (M4-M8) onto the ``ice_api.models`` ORM
rows. Because the AI stages emit string-slug ids (``"python.classes"``,
``"cp_1"``, ``"ex_cp_1_coding"``) while the ORM uses autoincrement integers,
each persist function returns an id-lookup map that the next stage consumes.

All functions reuse ``ice_shared.db`` (RLS-aware async sessions). On SQLite
dev the RLS branch is a no-op; on Postgres the tenant GUC is set via
``set_tenant_context`` before the session opens.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

# Importing ice_api.models registers every table on the shared Base (side
# effect of class definition) so create_all / ORM inserts resolve.
from ice_api.models import (  # noqa: E402
    Artifact,
    Checkpoint,
    Concept,
    ConceptEdge,
    Curriculum,
    CurriculumStatus,
    Exercise,
    ExerciseType,
    Segment,
    Test,
)
from ice_shared.db import get_session_factory, set_tenant_context

logger = logging.getLogger(__name__)

_EX_TYPES = ("mcq", "coding", "debug", "conceptual")


def _parse_cp_id(ex_id: str) -> str:
    """Recover the checkpoint slug from an exercise id ``ex_<cp_id>_<type>``."""
    rest = ex_id[len("ex_"):] if ex_id.startswith("ex_") else ex_id
    for t in _EX_TYPES:
        suffix = f"_{t}"
        if rest.endswith(suffix):
            return rest[: -len(suffix)]
    return rest


def _ex_type(value: str) -> ExerciseType:
    return ExerciseType(value)


async def set_curriculum_status(
    curriculum_id: Any, tenant_id: str, status: str, *, ready: bool = False
) -> None:
    """Flip the curriculum row status (queued|processing|ready|failed)."""
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    async with factory() as session:
        c = await session.get(Curriculum, int(curriculum_id))
        if c is None:
            logger.error("curriculum %s not found", curriculum_id)
            return
        c.status = CurriculumStatus(status)
        if ready:
            c.ready_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()


async def update_curriculum_meta(
    curriculum_id: Any,
    tenant_id: str,
    *,
    title: str | None = None,
    duration: float | None = None,
    language: str | None = None,
    source_type: str | None = None,
    source_ref: str | None = None,
) -> None:
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    async with factory() as session:
        c = await session.get(Curriculum, int(curriculum_id))
        if c is None:
            return
        if title is not None:
            c.title = title
        if duration is not None:
            c.duration = duration
        if language is not None:
            c.language = language
        if source_type is not None:
            c.source_type = source_type
        if source_ref is not None:
            c.source_ref = source_ref
        await session.commit()


async def save_artifact(
    curriculum_id: Any,
    tenant_id: str,
    kind: str,
    storage_uri: str,
    meta: dict[str, Any] | None = None,
) -> None:
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    async with factory() as session:
        row = Artifact(
            tenant_id=int(tenant_id),
            curriculum_id=int(curriculum_id),
            kind=kind,
            storage_uri=storage_uri,
            meta=meta or {},
        )
        session.add(row)
        await session.commit()


async def persist_segments(
    curriculum_id: Any, tenant_id: str, segments: list[dict[str, Any]]
) -> dict[str, int]:
    """Insert Segment rows; return {segment_id(str): orm_id(int)}."""
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    seg_map: dict[str, int] = {}
    async with factory() as session:
        for seg in segments:
            row = Segment(
                curriculum_id=int(curriculum_id),
                start_time=seg.get("start"),
                end_time=seg.get("end"),
                title=seg.get("title"),
                summary=seg.get("summary"),
                structuredness=seg.get("structuredness"),
                topic_label=seg.get("topic_label"),
                confidence=seg.get("confidence"),
            )
            session.add(row)
            await session.flush()
            seg_map[str(seg["id"])] = int(row.id)
        await session.commit()
    logger.info("persisted %d segments", len(seg_map))
    return seg_map


async def persist_concepts(
    curriculum_id: Any, tenant_id: str, graph: dict[str, Any]
) -> dict[str, int]:
    """Insert Concept rows; return {concept_slug: orm_id}."""
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    concept_map: dict[str, int] = {}
    concepts = graph.get("concepts", []) if isinstance(graph, dict) else []
    async with factory() as session:
        for c in concepts:
            row = Concept(
                curriculum_id=int(curriculum_id),
                label=c.get("label") or c.get("id") or "concept",
                description=c.get("description"),
                difficulty=float(c.get("difficulty", 1.5)),
            )
            session.add(row)
            await session.flush()
            concept_map[str(c["id"])] = int(row.id)
        await session.commit()
    logger.info("persisted %d concepts", len(concept_map))
    return concept_map


async def persist_edges(
    tenant_id: str, graph: dict[str, Any], concept_map: dict[str, int]
) -> None:
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    async with factory() as session:
        for e in edges:
            src = concept_map.get(str(e.get("src_concept_id")))
            dst = concept_map.get(str(e.get("dst_concept_id")))
            if src is None or dst is None:
                continue
            session.add(
                ConceptEdge(
                    source_id=src,
                    target_id=dst,
                    relation=str(e.get("relation", "related")),
                )
            )
        await session.commit()
    logger.info("persisted %d concept edges", len(edges))


async def persist_checkpoints(
    curriculum_id: Any,
    tenant_id: str,
    checkpoints: list[dict[str, Any]],
    seg_map: dict[str, int],
    concept_map: dict[str, int],
) -> dict[str, int]:
    """Insert Checkpoint rows; return {checkpoint_slug: orm_id}."""
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    cp_map: dict[str, int] = {}
    async with factory() as session:
        for cp in checkpoints:
            row = Checkpoint(
                curriculum_id=int(curriculum_id),
                segment_id=seg_map.get(str(cp.get("segment_id"))),
                concept_id=concept_map.get(str(cp.get("concept_id"))),
                ts=float(cp.get("ts", 0.0)),
                exercise_type=_ex_type(cp.get("exercise_type", "mcq")),
                difficulty=float(cp.get("difficulty", 3)),
            )
            session.add(row)
            await session.flush()
            cp_map[str(cp["id"])] = int(row.id)
        await session.commit()
    logger.info("persisted %d checkpoints", len(cp_map))
    return cp_map


async def persist_exercises(
    tenant_id: str, exercises: list[dict[str, Any]], cp_map: dict[str, int]
) -> dict[str, int]:
    """Insert Exercise rows; return {exercise_id(str): orm_id}.

    The type-specific payload (mcq/coding/debug/conceptual) is stored as JSON
    in ``Exercise.payload``; the envelope fields populate the scalar columns.
    """
    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    ex_map: dict[str, int] = {}
    async with factory() as session:
        for ex in exercises:
            cp_slug = _parse_cp_id(str(ex.get("id", "")))
            etype = _ex_type(ex.get("type", "mcq"))
            payload = None
            for t in _EX_TYPES:
                if t in ex and isinstance(ex[t], (dict, list)):
                    payload = ex[t]
                    break
            row = Exercise(
                checkpoint_id=cp_map.get(cp_slug),
                type=etype,
                payload=payload,
                confidence=float(ex.get("confidence", 0.0)),
                validation_passed=bool(ex.get("validation_passed", False)),
            )
            session.add(row)
            await session.flush()
            ex_map[str(ex["id"])] = int(row.id)
        await session.commit()
    logger.info("persisted %d exercises", len(ex_map))
    return ex_map


async def persist_tests(
    tenant_id: str,
    exercises: list[dict[str, Any]],
    ex_map: dict[str, int],
) -> None:
    """For each coding exercise, run M8 and persist Test rows.

    Updates the parent Exercise.validation_passed from the M8 result.
    NOTE: mutation_score has no ORM column; it is logged only.
    """
    from ice_test_gen import generate_tests

    set_tenant_context(str(tenant_id))
    factory = get_session_factory()
    async with factory() as session:
        for ex in exercises:
            if ex.get("type") != "coding":
                continue
            orm_id = ex_map.get(str(ex["id"]))
            if orm_id is None:
                continue
            try:
                result = generate_tests(ex)
            except Exception as exc:
                logger.warning("M8 failed for %s: %s", ex.get("id"), exc)
                continue
            for assert_str in result.get("tests_visible", []):
                session.add(
                    Test(
                        exercise_id=orm_id,
                        kind="visible",
                        input=assert_str,
                        weight=1.0,
                    )
                )
            for assert_str in result.get("tests_hidden", []):
                session.add(
                    Test(
                        exercise_id=orm_id,
                        kind="hidden",
                        input=assert_str,
                        weight=1.0,
                    )
                )
            # Flip the parent exercise's validation flag.
            ex_row = await session.get(Exercise, orm_id)
            if ex_row is not None:
                ex_row.validation_passed = bool(result.get("validation_passed", False))
            logger.info(
                "M8 %s: mutation_score=%.3f validation_passed=%s",
                ex.get("id"),
                float(result.get("mutation_score", 0.0)),
                result.get("validation_passed"),
            )
        await session.commit()
