import asyncio
import json
import logging
import math
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ice_api.models import Artifact, Curriculum
from ice_shared import settings
from ice_shared.db import Base, get_engine, get_session_factory, reset_engine, set_tenant_context
from ice_shared.s3 import get_s3_client
from sqlalchemy import text, select

from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sentinel statuses mirrored from the curriculum model so this task stays
# decoupled from the ORM enum definition.
_STATUS_SKIPPED = "skipped"


def _remotion_project_dir() -> str:
    """Return the Remotion project copied beside worker under /app/apps."""
    configured = settings.signal_video.remotion_project_dir.strip()
    if configured:
        return os.path.abspath(configured)
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "remotion")
    )


def _remotion_command(project_dir: str, output_path: str, props_path: str) -> list[str]:
    configured = settings.signal_video.remotion_command.strip()
    executable = configured or os.path.join(
        project_dir, "node_modules", ".bin", "remotion"
    )
    if not os.path.isabs(executable):
        executable = _preflight_binary(executable) or executable
    return [
        executable,
        "render",
        "src/index.ts",
        "MainComp",
        output_path,
        "--props",
        props_path,
    ]


async def _ensure_tables() -> None:
    import ice_api.models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)


async def _set_status(
    curriculum_id: uuid.UUID, tenant_id: str, status: str, url: str | None = None
) -> None:
    set_tenant_context(tenant_id)
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import update
        values = {"signal_status": status}
        if url:
            values["signal_video_url"] = url
        await session.execute(update(Curriculum).where(Curriculum.id == curriculum_id).values(**values))
        await session.commit()


def _preflight_binary(name: str) -> str | None:
    """Return the absolute path to ``name`` on PATH, or None if unavailable.

    Running edge-tts / npx blindly and swallowing the failure produced
    confusing "failed" statuses with no clear cause. Failing fast here turns
    a missing-binary runtime error into an explicit, loggable skip.
    """
    return shutil.which(name)


def get_audio_duration(file_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _generate_tts(sentence: str, out_path: str) -> str | None:
    """Synthesize one sentence to ``out_path`` via edge-tts.

    Returns the output path on success, None on failure. Kept as a plain
    function (no async) so it can run in a ThreadPoolExecutor for real
    parallelism — the per-slide TTS round-trips were the dominant serial cost.
    """
    cmd = [
        settings.signal_video.tts_command,
        "--voice",
        settings.signal_video.tts_voice,
        "--text",
        sentence,
        "--write-media",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
        logger.error("TTS produced no output for sentence: %s", sentence[:80])
        return None
    except Exception as e:
        logger.error("TTS failed for sentence '%s': %s", sentence[:80], e)
        return None


def create_ass_subtitle(text: str, duration: float, out_path: str):
    # A simple ASS subtitle file for one line of caption. Kept as the
    # ffmpeg-engine subtitle path (and as documentation of the format); the
    # remotion engine burns captions via its own components.
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {settings.signal_video.width}
PlayResY: {settings.signal_video.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Roboto,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,2,20,20,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:{duration:05.2f},Default,,0,0,0,,{text}
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


async def _run_signal_video(curriculum_id_str: str, tenant_id: str) -> None:
    reset_engine()
    curriculum_id = uuid.UUID(curriculum_id_str)
    set_tenant_context(tenant_id)
    await _ensure_tables()

    # Master toggle: the signal video is a nice-to-have. When disabled the
    # task marks the curriculum skipped and exits without touching Gemini /
    # Remotion / TTS, so a CPU-only free tier is never blocked by this feature.
    if not settings.signal_video.enabled:
        logger.info(
            "Signal video disabled (SIGNAL_VIDEO_ENABLED=false); skipping cid=%s", curriculum_id
        )
        await _set_status(curriculum_id, tenant_id, _STATUS_SKIPPED)
        return

    # Preflight the binaries this task depends on. Failing fast with a clear
    # log beats spawning a subprocess that errors and swallowing the cause.
    if not _preflight_binary(settings.signal_video.tts_command):
        logger.error(
            "Signal video aborting: TTS binary '%s' not on PATH",
            settings.signal_video.tts_command,
        )
        await _set_status(curriculum_id, tenant_id, "failed")
        return
    engine = settings.signal_video.engine
    remotion_dir = _remotion_project_dir()
    if engine == "remotion":
        required = (
            os.path.join(remotion_dir, "src", "index.ts"),
            os.path.join(remotion_dir, "package.json"),
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            logger.error(
                "Signal video aborting: invalid Remotion project dir=%s missing=%s module=%s",
                remotion_dir,
                missing,
                __file__,
            )
            await _set_status(curriculum_id, tenant_id, "failed")
            return
    await _set_status(curriculum_id, tenant_id, "processing")

    factory = get_session_factory()
    async with factory() as session:
        curriculum = (await session.execute(select(Curriculum).where(Curriculum.id == curriculum_id))).scalar_one_or_none()
        if not curriculum:
            raise ValueError(f"Curriculum {curriculum_id} not found")

        target_duration = (
            min(1 + 0.5 * math.log(max(1, curriculum.duration or 3600) / 60.0), 3.5) * 60
        )
        # ~130 words per min = max words
        max_words = int((target_duration / 60) * 130)

        # load transcript


        stmt = select(Artifact).where(
            Artifact.curriculum_id == curriculum_id, Artifact.kind == "transcript"
        )
        res = await session.execute(stmt)
        transcript_art = res.scalars().first()

    if not transcript_art:
        await _set_status(curriculum_id, tenant_id, "failed")
        raise ValueError("Transcript not found")

    s3 = get_s3_client()
    with tempfile.TemporaryDirectory() as tmpdir:
        transcript_path = os.path.join(tmpdir, "transcript.json")
        s3.download_file(settings.s3.bucket, transcript_art.storage_uri, transcript_path)
        with open(transcript_path) as f:
            transcript_data = json.load(f)

        sentences = []
        for seg in transcript_data.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                sentences.append(text)

        full_text = " ".join(sentences)

        # Call Gemini (dynamic model selection w/ fallback — shared with recap).
        # Hardcoding the model name silently broke this task when the name was
        # not served; list_models() + fallback makes failures loud.
        from ice_worker.tasks._gemini import get_gemini_model

        model = get_gemini_model(generation_config={"response_mime_type": "application/json"})

        # Cap the transcript sent to Gemini. Sending 50k chars made generation
        # slower and costlier with no summary-quality benefit; 12k is ample
        # signal for a <=6-slide summary.
        transcript_chars = settings.signal_video.transcript_chars
        max_slides = settings.signal_video.max_slides
        prompt = f"""You are an expert documentary producer and technical educator. Select the highest-signal sentences from the transcript to form a summary of AT MOST {max_words} words and NO MORE THAN {max_slides} sentences.

For each sentence provide:
1. `theme`: one of "tech","warning","success","creative","dark","neon","nature","academic".
2. `codeSnippet` (optional): the EXACT code the sentence references, only if it is explicitly about code.
3. `codeLanguage` (optional): e.g. "python","javascript","bash".

Return a JSON array of EXACTLY this shape:
[
  {{"sentence": "A for loop lets you iterate over a range of numbers.", "theme": "tech", "codeSnippet": "for i in range(10):\\n    print(i)", "codeLanguage": "python"}},
  {{"sentence": "However, infinite loops will crash your program!", "theme": "warning"}}
]

Transcript:
{full_text[:transcript_chars]}
"""
        logger.info(
            f"Sending prompt to Gemini for signal video (max words: {max_words}, max slides: {max_slides}, transcript chars: {transcript_chars})"
        )
        resp = model.generate_content(prompt)
        try:
            clean_text = resp.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            segments = json.loads(clean_text)
        except Exception as e:
            logger.error(f"Gemini failed: {e}")
            await _set_status(curriculum_id, tenant_id, "failed")
            return

        slides_data = []

        # Cap slide count so render time stays bounded on CPU. Gemini may
        # return more than max_slides; keep the first N.
        selected = (
            segments[: settings.signal_video.max_slides] if isinstance(segments, list) else []
        )

        # TTS: run the per-slide edge-tts calls in a thread pool instead of
        # serially. Each call is a blocking network round-trip (~1-2s), so N
        # slides took N*2s serially; a small pool collapses that to ~max(2s,
        # ceil(N/workers)*2s). edge-tts is a CLI -> no GIL contention.
        # Audio is written under remotion/public/tmp_audio (remotion's
        # staticFile() only resolves files under public/) and removed in a
        # finally below so the source tree doesn't accumulate render artifacts.
        audio_public_dir = os.path.join(remotion_dir, "public", "tmp_audio")
        os.makedirs(audio_public_dir, exist_ok=True)

        def _build_slide(idx_seg):
            idx, seg = idx_seg
            sentence = (seg.get("sentence") or "").strip()
            if not sentence:
                return None
            audio_filename = f"audio_{curriculum_id}_{idx}.mp3"
            audio_path = os.path.join(audio_public_dir, audio_filename)
            if not _generate_tts(sentence, audio_path):
                return None
            audio_dur = get_audio_duration(audio_path)
            if audio_dur <= 0:
                return None
            return {
                "text": sentence,
                "durationInFrames": int(math.ceil(audio_dur * 30)),
                "audioPath": f"tmp_audio/{audio_filename}",
                "theme": seg.get("theme", "dark"),
                "codeSnippet": seg.get("codeSnippet"),
                "codeLanguage": seg.get("codeLanguage"),
            }

        tts_workers = min(len(selected), 4)
        with ThreadPoolExecutor(max_workers=tts_workers or 1) as pool:
            for slide in pool.map(_build_slide, enumerate(selected)):
                if slide is not None:
                    slides_data.append(slide)

        if not slides_data:
            await _set_status(curriculum_id, tenant_id, "failed")
            return

        # Write props for the chosen engine. width/height drive the Remotion
        # composition resolution (defaults to 1280x720 — see Root.tsx).
        props_path = os.path.join(tmpdir, "props.json")
        with open(props_path, "w") as f_props:
            json.dump(
                {
                    "slides": slides_data,
                    "width": settings.signal_video.width,
                    "height": settings.signal_video.height,
                },
                f_props,
            )

        final_video_path = os.path.join(tmpdir, "signal_video.mp4")

        if engine != "remotion":
            logger.error("Signal video engine '%s' is not supported yet", engine)
            await _set_status(curriculum_id, tenant_id, "failed")
            return

        # 4. Run the project-local Remotion CLI. The configured command is an
        # executable, not an npx launcher, so argv has one unambiguous shape.
        render_cmd = _remotion_command(remotion_dir, final_video_path, props_path)
        if not os.path.isfile(render_cmd[0]) and not _preflight_binary(render_cmd[0]):
            logger.error(
                "Signal video aborting: Remotion CLI not found: %s",
                render_cmd[0],
            )
            await _set_status(curriculum_id, tenant_id, "failed")
            return
        logger.info(
            "Rendering Remotion video argv=%r cwd=%s module=%s",
            render_cmd,
            remotion_dir,
            __file__,
        )
        try:
            res_render = subprocess.run(
                render_cmd,
                cwd=remotion_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if res_render.returncode != 0:
                logger.error("Remotion render error: %s\n%s", res_render.stderr, res_render.stdout)
        except Exception as render_exc:
            logger.error(f"Remotion render subprocess failed: {render_exc}", exc_info=True)
            await _set_status(curriculum_id, tenant_id, "failed")
            return
        finally:
            # Always clean the transient render audio so it can't leak into the
            # repo or the next run.
            try:
                shutil.rmtree(audio_public_dir, ignore_errors=True)
            except Exception:
                pass

        if not os.path.exists(final_video_path):
            logger.error("Remotion render produced no output file at %s", final_video_path)
            await _set_status(curriculum_id, tenant_id, "failed")
            return

        # 5. Upload to S3
        s3_key = f"tenants/{tenant_id}/curricula/{curriculum_id}/signal_video.mp4"
        s3.upload_file(
            final_video_path, settings.s3.bucket, s3_key, ExtraArgs={"ContentType": "video/mp4"}
        )

        async with factory() as session:
            new_art = Artifact(
                tenant_id=tenant_id,
                curriculum_id=curriculum_id,
                kind="signal_video",
                storage_uri=s3_key,
            )
            session.add(new_art)

            await session.commit()

        # Build a simple public URL via the external endpoint.
        # The MinIO bucket has public-download policy so no presigned
        # signature is needed — avoids signature-invalidation when the
        # hostname changes (e.g. plain IP vs sslip.io proxy).
        external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000").rstrip("/")
        public_url = f"{external_endpoint}/{settings.s3.bucket}/{s3_key}"

        await _set_status(curriculum_id, tenant_id, "ready", public_url)


async def _run_with_failover(curriculum_id: str, tenant_id: str) -> None:
    try:
        await _run_signal_video(curriculum_id, tenant_id)
    except Exception as exc:
        logger.error(f"Signal video generation failed: {exc}", exc_info=True)
        try:
            await _set_status(uuid.UUID(curriculum_id), tenant_id, "failed")
        except Exception:
            pass
        raise


@celery_app.task(
    name="ice.worker.generate_signal_video",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=1,
)
def generate_signal_video(self: Any, curriculum_id: str, tenant_id: str) -> None:
    logger.info("generate_signal_video: cid=%s tenant=%s", curriculum_id, tenant_id)
    reset_engine()
    asyncio.run(_run_with_failover(curriculum_id, tenant_id))
