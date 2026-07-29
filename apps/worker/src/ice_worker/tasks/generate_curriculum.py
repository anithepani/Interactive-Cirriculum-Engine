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
from sqlalchemy import text

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
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
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


async def _get_curriculum_details(curriculum_id: str) -> tuple[str, int | None]:
    """Read learner-selected difficulty and user_id off the curriculum row."""
    try:
        from ice_api.models import Curriculum
        from ice_shared.db import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            c = await session.get(Curriculum, curriculum_id)
            value = str(getattr(c, "difficulty", None) or "medium").strip().lower()
            diff = value if value in ("easy", "medium", "hard") else "medium"
            uid = c.user_id if c else None
            return diff, uid
    except Exception:
        logger.warning(
            "could not read details for curriculum %s; defaulting to medium/none",
            curriculum_id,
        )
        return "medium", None


def _build_segment_texts(transcript: dict, segments: list[dict]) -> dict[str, str]:
    """Build a ``{segment_id: transcript_text}`` map for exercise grounding.

    M4 segment dicts carry only ``summary`` (no raw text), so we reconstruct
    each segment's real transcript by concatenating the transcript's raw
    segments whose midpoint falls within the M4 segment's [start, end] window.
    This gives the exercise generator the actual spoken content to ground on.
    Best-effort: returns ``{}`` on any problem so M7 falls back to summaries.
    """
    try:
        raw = transcript.get("segments") or []
        if not raw:
            return {}
        text_map: dict[str, str] = {}
        for seg in segments:
            sid = str(seg.get("id", ""))
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))
            parts: list[str] = []
            for r in raw:
                r_start = float(r.get("start", 0.0))
                r_end = float(r.get("end", r_start))
                mid = (r_start + r_end) / 2.0
                if start <= mid <= end:
                    txt = (r.get("text") or "").strip()
                    if txt:
                        parts.append(txt)
            if parts:
                text_map[sid] = " ".join(parts)
        return text_map
    except Exception:
        logger.warning("could not build per-segment transcript texts; using summaries")
        return {}


def _build_segment_instructor_code(
    visual_items: list, segments: list[dict]
) -> dict[str, str]:
    """Build a ``{segment_id: code}`` map from M3 vision OCR code items.

    Phase 5 grounding guarantee: the checkpoint placer only allows coding/debug
    exercises on a segment when there is concrete evidence it is about code.
    Here we key each OCR ``code`` visual item to the segment whose [start, end]
    window contains its timestamp, so the placer can gate code exercises per
    segment. Best-effort: returns ``{}`` on any problem (the placer then falls
    back to the transcript-text technicality heuristic).
    """
    try:
        if not visual_items or not segments:
            return {}

        def _vi_field(vi, name):
            if isinstance(vi, dict):
                return vi.get(name)
            return getattr(vi, name, None)

        def _vi_type(vi) -> str:
            t = _vi_field(vi, "type")
            return str(getattr(t, "value", t) or "").lower()

        code_map: dict[str, list[str]] = {}
        for vi in visual_items:
            if _vi_type(vi) != "code":
                continue
            text = _vi_field(vi, "text")
            if not text or not str(text).strip():
                continue
            try:
                ts = float(_vi_field(vi, "ts") or 0.0)
            except (TypeError, ValueError):
                continue
            for seg in segments:
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
                if start <= ts <= end:
                    sid = str(seg.get("id", ""))
                    code_map.setdefault(sid, []).append(str(text))
                    break
        return {sid: "\n\n".join(parts) for sid, parts in code_map.items() if parts}
    except Exception:
        logger.warning("could not build per-segment instructor code; skipping")
        return {}


async def _run(curriculum_id: str, video_ref: str, tenant_id: str) -> None:
    set_tenant_context(tenant_id)
    await _ensure_tables()
    await persist.set_curriculum_status(curriculum_id, tenant_id, "processing")

    # Fetch curriculum details
    difficulty, user_id = await _get_curriculum_details(curriculum_id)

    async def publish_progress(message: str) -> None:
        """Publish a live progress message to the user via Redis SSE stream."""
        if not user_id:
            return
        try:
            import redis.asyncio as aioredis
            r = aioredis.Redis.from_url(settings.redis.url)
            channel = f"ice:notifications:{user_id}"
            payload = json.dumps({
                "type": "curriculum_progress",
                "curriculum_id": curriculum_id,
                "message": message
            })
            await r.publish(channel, payload)
            await r.aclose()
        except Exception as e:
            logger.warning("failed to publish progress: %s", e)

    await publish_progress("Initializing AI pipeline...")

    # ---- M1: ingest ----
    if _is_youtube_ref(video_ref):
        from ice_ingestion import ingest_video
        
        await publish_progress("Downloading YouTube video...")
        ingest = ingest_video(video_ref, tenant_id, curriculum_id)
        source_type = "youtube"
    elif _is_upload_ref(video_ref):
        from ice_ingestion import ingest_upload

        await publish_progress("Processing uploaded video...")
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
    await publish_progress("Extracting speech and transcribing...")
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

    # ---- M3: extract visuals ----
    await publish_progress("Extracting visual content & code snippets...")
    visual_items = []
    try:
        from ice_ingestion import extract_visuals

        loop = asyncio.get_running_loop()
        # visual_items = await loop.run_in_executor(
        #     None,
        #     lambda: extract_visuals(video_path, extract_rate_sec=settings.vision.extract_rate_sec)
        # )
        
        # Disabled per user request to test generation without OCR
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

    # ---- M5: concepts ----
    await publish_progress("Building Concept Knowledge Graph...")
    from ice_concept_graph import extract_concepts_and_edges
    from ice_exercise_gen import generate_concept_reviews

    graph = extract_concepts_and_edges(segments)
    
    await publish_progress("Generating concept reviews...")
    # Reconstruct a compact transcript string to ground the review payload
    transcript_text = " ".join(
        str(r.get("text") or "").strip()
        for r in (transcript.get("segments") or [])
        if str(r.get("text") or "").strip()
    )
    graph["concepts"] = generate_concept_reviews(graph.get("concepts", []), transcript_text)

    concept_map = await persist.persist_concepts(curriculum_id, tenant_id, graph)
    await persist.persist_edges(tenant_id, graph, concept_map)

    # ---- Phase 5: classify curriculum content ----
    # Lightweight, called once per curriculum. Drives dynamic exercise-type
    # relevance in M6 (candidate pool) and M7 (prompt context). Best-effort:
    # the classifier itself never raises (LLM failure -> keyword fallback), but
    # we still guard so a missing category can never break generation.
    from ice_checkpoints import classify_content

    # Reconstruct a compact transcript string for the classifier.
    transcript_text = " ".join(
        str(r.get("text") or "").strip()
        for r in (transcript.get("segments") or [])
        if str(r.get("text") or "").strip()
    )
    try:
        classification = classify_content(segments, graph, transcript_text)
    except Exception:
        logger.warning("Phase 5 classify_content failed; defaulting category")
        classification = {"category": None, "confidence": 0.0}
    content_category = classification.get("category")
    logger.info(
        "Phase 5 content category=%s (conf=%.2f) for curriculum %s",
        content_category,
        float(classification.get("confidence", 0.0) or 0.0),
        curriculum_id,
    )

    # ---- M6: checkpoints ----
    await publish_progress("Placing interactive checkpoints...")
    from ice_checkpoints import place_checkpoints

    # Phase 5 grounding guarantee: build a {segment_id: code} map from the M3
    # vision OCR items so the placer only permits coding/debug on segments that
    # actually have on-screen code (or technical transcript evidence). Empty
    # map -> the placer falls back to the transcript-text heuristic.
    seg_instructor_code = _build_segment_instructor_code(visual_items, segments)

    checkpoints = place_checkpoints(
        segments,
        graph,
        min_gap_sec=settings.pipeline.checkpoint_min_gap_sec,
        min_start_sec=settings.pipeline.checkpoint_min_start_sec,
        avoid_final_sec=settings.pipeline.checkpoint_avoid_final_sec,
        difficulty=difficulty,
        category=content_category,
        instructor_code=seg_instructor_code,
    )
    cp_map = await persist.persist_checkpoints(
        curriculum_id, tenant_id, checkpoints, seg_map, concept_map
    )

    # ---- M7: exercises ----
    await publish_progress("Generating interactive exercises...")
    from ice_exercise_gen import generate_exercises

    # Feed the instructor's on-screen code (M3 vision OCR) into M7 so coding/
    # debug prompts are grounded in the real lesson context (Phase 4, Task 3).
    # Issue 3: the per-segment ``seg_instructor_code`` map (built above) is the
    # PRIMARY grounding source passed as ``segment_code`` — it scopes each
    # checkpoint to its OWN segment's code so unrelated code from other segments
    # never leaks into a snippet. This flat list is only a last-resort fallback
    # for checkpoints whose segment has no scoped code. If vision failed or
    # produced no code regions this is an empty list and M7 behaves as before.
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

    # Phase 4 grounding: reconstruct each segment's real transcript text from
    # the raw transcript so M7 grounds exercises on what was actually said (not
    # just the LLM summary). Empty map falls back to summaries (zero-regression).
    segment_texts = _build_segment_texts(transcript, segments)

    exercises = generate_exercises(
        checkpoints, segments, graph,
        instructor_code=instructor_code,
        segment_texts=segment_texts,
        category=content_category,
        segment_code=seg_instructor_code,
    )
    ex_map = await persist.persist_exercises(tenant_id, exercises, cp_map)

    # ---- M8: validate tests (gated) ----
    if settings.pipeline.run_tests:
        await persist.persist_tests(tenant_id, exercises, ex_map)

    await persist.set_curriculum_status(curriculum_id, tenant_id, "ready", ready=True)
    await publish_progress("Curriculum is ready!")
    logger.info("curriculum %s ready", curriculum_id)

    # Signal video auto-trigger disabled per user request


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
