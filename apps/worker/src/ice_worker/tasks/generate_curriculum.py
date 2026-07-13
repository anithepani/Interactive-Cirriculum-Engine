"""generate_curriculum: the end-to-end async AI pipeline as a Celery task.

Sequence: M1 ingest -> M2 transcribe -> M4 segment -> M5 concepts -> M6
checkpoints -> M7 exercises -> (M8 tests, gated by PIPELINE_RUN_TESTS).

Each stage's output is persisted to the DB via ice_worker.persist (ORM). The
curriculum row status transitions queued -> processing -> ready (or failed on
error). The API dispatches this task via send_task() so it never imports the
worker package (keeps Celery / yt-dlp out of the API process).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
from typing import Any

from ice_shared import settings
from ice_shared.db import Base, get_engine, reset_engine, set_tenant_context

from ice_worker import persist
from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Windows asyncio fix (matches db/seed/seed.py). Harmless on Linux.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _ensure_tables() -> None:
    """Idempotently create the ORM tables if missing.

    Importing ice_api.models registers every table on the shared Base; then
    create_all is a no-op for tables that already exist. NOT to be confused
    with scripts/init_db.py (a divergent stale schema).
    """
    import ice_api.models  # noqa: F401  (side effect: registers tables)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _run(curriculum_id: str, video_ref: str, tenant_id: str) -> None:
    set_tenant_context(tenant_id)
    await _ensure_tables()
    await persist.set_curriculum_status(curriculum_id, tenant_id, "processing")

    # ---- M1: ingest (yt-dlp + ffmpeg + MinIO) ----
    from ice_ingestion import ingest_video

    ingest = ingest_video(video_ref, tenant_id, curriculum_id)
    await persist.update_curriculum_meta(
        curriculum_id,
        tenant_id,
        title=ingest["title"],
        duration=ingest["duration_sec"],
        language=ingest["language_hint"],
        source_type="youtube",
        source_ref=video_ref,
    )
    await persist.save_artifact(
        curriculum_id, tenant_id, "audio", ingest["s3_key"]
    )
    audio_path = ingest["audio_path"]

    # ---- M2: transcribe (faster-whisper, tiny / cpu / int8) ----
    from ice_transcript import transcribe

    transcript = transcribe(audio_path)
    await persist.save_artifact(
        curriculum_id,
        tenant_id,
        "transcript",
        f"tenants/{tenant_id}/curricula/{curriculum_id}/transcript.json",
        meta={"language": transcript.get("language")},
    )
    with contextlib.suppress(OSError):
        os.remove(audio_path)
    # ---- M4: segment transcript ----
    from ice_segmentation import segment_transcript

    segments = segment_transcript(transcript)
    seg_map = await persist.persist_segments(curriculum_id, tenant_id, segments)

    # ---- M5: concept graph ----
    from ice_concept_graph import extract_concepts_and_edges

    graph = extract_concepts_and_edges(segments)
    concept_map = await persist.persist_concepts(curriculum_id, tenant_id, graph)
    await persist.persist_edges(tenant_id, graph, concept_map)

    # ---- M6: place checkpoints ----
    from ice_checkpoints import place_checkpoints

    checkpoints = place_checkpoints(
        segments,
        graph,
        min_gap_sec=settings.pipeline.checkpoint_min_gap_sec,
        min_start_sec=settings.pipeline.checkpoint_min_start_sec,
        avoid_final_sec=settings.pipeline.checkpoint_avoid_final_sec,
    )
    cp_map = await persist.persist_checkpoints(
        curriculum_id, tenant_id, checkpoints, seg_map, concept_map
    )

    # ---- M7: generate exercises ----
    from ice_exercise_gen import generate_exercises

    exercises = generate_exercises(checkpoints, segments, graph)
    ex_map = await persist.persist_exercises(tenant_id, exercises, cp_map)

    # ---- M8: validate tests (gated) ----
    if settings.pipeline.run_tests:
        await persist.persist_tests(tenant_id, exercises, ex_map)

    await persist.set_curriculum_status(curriculum_id, tenant_id, "ready", ready=True)
    logger.info("curriculum %s ready", curriculum_id)


async def _mark_failed(
    curriculum_id: str, tenant_id: str, reason: str
) -> None:
    try:
        await persist.set_curriculum_status(curriculum_id, tenant_id, "failed")
        logger.error("curriculum %s FAILED: %s", curriculum_id, reason)
    except Exception:
        logger.exception("could not mark curriculum %s as failed", curriculum_id)


async def _run_with_failover(
    curriculum_id: str, video_ref: str, tenant_id: str
) -> None:
    """Run the pipeline; on failure mark the row failed within the same event loop.

    Sharing the loop avoids the dead-asyncpg-pool issue where a second
    asyncio.run creates a fresh loop whose pooled connections are bound to
    the now-closed first loop.
    """
    try:
        await _run(curriculum_id, video_ref, tenant_id)
    except Exception as exc:
        await _mark_failed(curriculum_id, tenant_id, str(exc))
        raise


@celery_app.task(  # type: ignore[untyped-decorator]
    name="ice_worker.tasks.generate_curriculum.generate_curriculum",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=60,
    retry_jitter=False,
)
def generate_curriculum(
    self: Any, curriculum_id: str, video_ref: str, tenant_id: str
) -> str:
    """Run the full AI pipeline for one curriculum. Dispatched by the API."""
    logger.info(
        "generate_curriculum: cid=%s video=%s tenant=%s",
        curriculum_id, video_ref, tenant_id,
    )
    # Drop any engine singleton from a previous asyncio.run in this worker
    # process — its asyncpg pool is bound to a now-closed event loop.
    reset_engine()
    asyncio.run(_run_with_failover(curriculum_id, video_ref, tenant_id))
    return curriculum_id
