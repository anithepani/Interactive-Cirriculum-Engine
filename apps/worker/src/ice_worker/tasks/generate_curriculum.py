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
import json
import logging
import os
import re
import sys
import tempfile
from typing import Any

from ice_shared import settings
from ice_shared.db import Base, get_engine, reset_engine, set_tenant_context
from ice_shared.s3 import get_s3_client

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


_YT_REF_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/))"
    r"([A-Za-z0-9_-]{11})"
)


def _is_youtube_ref(video_ref: str) -> bool:
    """True when ``video_ref`` is a YouTube URL the yt-dlp path can ingest."""
    return bool(video_ref) and bool(_YT_REF_RE.search(video_ref))


def _is_upload_ref(video_ref: str) -> bool:
    """True when ``video_ref`` is an S3 key for a previously-uploaded video.

    The upload endpoint stores the raw file at
    ``tenants/<tid>/curricula/<cid>/source_video<ext>`` and sets that key as the
    curriculum's ``source_ref``. We detect it structurally (tenant-scoped key,
    not a URL) so the worker can route it to the local-file ingest path.
    """
    if not video_ref:
        return False
    if _is_youtube_ref(video_ref):
        return False
    if video_ref.startswith(("http://", "https://")):
        return False
    return video_ref.startswith("tenants/") and "/curricula/" in video_ref


async def _run(curriculum_id: str, video_ref: str, tenant_id: str) -> None:
    set_tenant_context(tenant_id)
    await _ensure_tables()
    await persist.set_curriculum_status(curriculum_id, tenant_id, "processing")

    # ---- M1: ingest ----
    # Two supported sources, routed by the shape of ``video_ref``:
    #   • YouTube URL  → ingest_video (yt-dlp + ffmpeg + caption harvest)
    #   • upload S3 key → ingest_upload (download from MinIO + ffmpeg)
    # Anything else (a bare filename, an unknown URL) can't be processed, so we
    # fail fast with a clear, user-facing reason rather than handing garbage to
    # yt-dlp and surfacing an opaque extractor error.
    if _is_youtube_ref(video_ref):
        from ice_ingestion import ingest_video

        ingest = ingest_video(video_ref, tenant_id, curriculum_id)
        source_type = "youtube"
    elif _is_upload_ref(video_ref):
        from ice_ingestion import ingest_upload

        ingest = ingest_upload(video_ref, tenant_id, curriculum_id)
        source_type = "upload"
    else:
        raise ValueError(
            "Unsupported source: expected a YouTube URL or an uploaded-file "
            f"reference, got {video_ref!r}."
        )

    await persist.update_curriculum_meta(
        curriculum_id,
        tenant_id,
        # For uploads the learner supplied the title at upload time (already on
        # the row); the ingest-derived name is just the S3 key basename, so
        # don't overwrite it. YouTube titles come from yt-dlp and are canonical.
        title=ingest["title"] if source_type == "youtube" else None,
        duration=ingest["duration_sec"],
        language=ingest["language_hint"],
        source_type=source_type,
        source_ref=video_ref,
    )
    await persist.save_artifact(
        curriculum_id, tenant_id, "audio", ingest["s3_key"]
    )
    if "s3_video_key" in ingest:
        await persist.save_artifact(
            curriculum_id, tenant_id, "video", ingest["s3_video_key"]
        )
    audio_path = ingest["audio_path"]
    video_path = ingest["video_path"]

    # ---- M2: transcribe ----
    # Caption harvesting (Block F): if M1 already produced a transcript from the
    # video's existing YouTube captions, reuse it and skip Whisper ASR entirely
    # (faster + cheaper). Otherwise fall back to faster-whisper as before.
    caption_transcript = ingest.get("caption_transcript")
    if caption_transcript and caption_transcript.get("segments"):
        transcript = caption_transcript
        logger.info(
            "M2: using harvested captions (%d segments) — skipping Whisper ASR",
            len(caption_transcript["segments"]),
        )
    else:
        from ice_transcript import transcribe

        transcript = transcribe(audio_path)

    # ─── Upload transcript JSON to S3 ─────────────────────────────────────────
    s3 = get_s3_client()
    s3_key = f"tenants/{tenant_id}/curricula/{curriculum_id}/transcript.json"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(transcript, f)
        f.flush()
        s3.upload_file(
            f.name,
            settings.s3.bucket,
            s3_key,
            ExtraArgs={'ContentType': 'application/json'}
        )
        os.unlink(f.name)  # clean up

    # Save artifact record
    await persist.save_artifact(
        curriculum_id,
        tenant_id,
        "transcript",
        s3_key,
        meta={"language": transcript.get("language")},
    )

    with contextlib.suppress(OSError):
        os.remove(audio_path)

    # ---- M3: extract visuals (fallback to transcript-only on failure) ----
    visual_items = []
    try:
        from ice_vision import extract_visuals
        loop = asyncio.get_running_loop()
        visual_items = await loop.run_in_executor(
            None,
            lambda: extract_visuals(video_path, extract_rate_sec=settings.vision.extract_rate_sec)
        )
    except Exception as e:
        logger.warning(f"M3 Visual Extraction failed: {e}. Falling back to transcript-only mode.")

    # Observability (Fix 3): surface how many visual items — and specifically
    # code regions (OCR) — vision produced. Empty code counts explain why
    # coding/debug exercises get no `context` snippet (e.g. AV1 decode issues).
    def _vi_type(vi) -> str:
        t = vi.get("type") if isinstance(vi, dict) else getattr(vi, "type", None)
        return str(getattr(t, "value", t) or "").lower()

    _code_items = sum(1 for vi in visual_items if _vi_type(vi) == "code")
    logger.info(
        "M3 visuals: %d items (%d code regions) for curriculum %s",
        len(visual_items),
        _code_items,
        curriculum_id,
    )

    with contextlib.suppress(OSError):
        os.remove(video_path)

    # ---- M4: segment transcript ----
    from ice_segmentation import segment_transcript

    segments = segment_transcript(transcript, visual_items=visual_items)
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

    # Feed the instructor's on-screen code (M3 vision OCR) into M7 so coding/
    # debug prompts are grounded in the real lesson context (Phase 4, Task 3).
    # Safe fallback: if vision failed or produced no code regions this is an
    # empty list and M7 behaves exactly as before.
    instructor_code: list[str] = []
    for vi in visual_items:
        if isinstance(vi, dict):
            vtype_val = vi.get("type")
            text = vi.get("text")
        else:
            vtype = getattr(vi, "type", None)
            vtype_val = getattr(vtype, "value", vtype)
            text = getattr(vi, "text", None)
        vtype_val = getattr(vtype_val, "value", vtype_val)
        if vtype_val == "code" and text and str(text).strip():
            instructor_code.append(str(text))

    exercises = generate_exercises(
        checkpoints, segments, graph, instructor_code=instructor_code
    )
    ex_map = await persist.persist_exercises(tenant_id, exercises, cp_map)

    # ---- M8: validate tests (gated) ----
    if settings.pipeline.run_tests:
        await persist.persist_tests(tenant_id, exercises, ex_map)

    await persist.set_curriculum_status(curriculum_id, tenant_id, "ready", ready=True)
    logger.info("curriculum %s ready", curriculum_id)

    # ── Auto-trigger cinematic summary (signal video) ──────────────────────────
    # Once the curriculum is ready, kick off the signal video automatically so
    # the learner doesn't have to press the button. Idempotent: if a signal is
    # already queued/processing/ready (e.g. the manual button was pressed first)
    # skip. A failure here must never fail the curriculum generation, so it's
    # fully isolated.
    try:
        from ice_api.models import Curriculum
        from ice_shared.db import get_session_factory

        should_dispatch = False
        factory = get_session_factory()
        async with factory() as session:
            c = await session.get(Curriculum, int(curriculum_id))
            if c and c.signal_status not in ("queued", "processing", "ready"):
                c.signal_status = "queued"
                await session.commit()
                should_dispatch = True
        if should_dispatch:
            celery_app.send_task(
                "ice.worker.generate_signal_video",
                args=[str(curriculum_id), str(tenant_id)],
            )
            logger.info("auto-triggered signal video for curriculum %s", curriculum_id)
    except Exception:
        logger.exception(
            "failed to auto-trigger signal video for curriculum %s",
            curriculum_id,
        )


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
