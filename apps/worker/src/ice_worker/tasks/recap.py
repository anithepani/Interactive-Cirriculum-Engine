from __future__ import annotations

import uuid

"""recap.py: Celery task to generate a 5-minute video recap.

This task takes an existing curriculum, fetches the video and transcript,
extracts the top ~300s of sentences by matching their embeddings against
the concept graph, and concatenates them using FFmpeg.
"""
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

from ice_api.models import Artifact, Concept, Curriculum
from ice_shared import settings
from ice_shared.db import Base, get_engine, get_session_factory, reset_engine, set_tenant_context
from ice_shared.s3 import get_s3_client, tenant_prefix
from sqlalchemy import text, select

from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

import math

# sentence-transformers removed

# Windows asyncio fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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
        values = {"recap_status": status}
        if url:
            values["recap_url"] = url
        await session.execute(update(Curriculum).where(Curriculum.id == curriculum_id).values(**values))
        await session.commit()


async def _run_recap(curriculum_id_str: str, tenant_id: str) -> None:
    curriculum_id = uuid.UUID(curriculum_id_str)
    set_tenant_context(tenant_id)
    await _ensure_tables()
    await _set_status(curriculum_id, tenant_id, "processing")

    factory = get_session_factory()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Fetch data
        async with factory() as session:
            from sqlalchemy import select

            art_stmt = select(Artifact).where(Artifact.curriculum_id == curriculum_id)
            artifacts = (await session.execute(art_stmt)).scalars().all()

            transcript_art = next((a for a in artifacts if a.kind == "transcript"), None)
            video_art = next((a for a in artifacts if a.kind == "video"), None)

            if not video_art:
                # Fallback: try audio (for backward compatibility)
                video_art = next((a for a in artifacts if a.kind == "audio"), None)
                logger.warning("Using audio artifact as video source; video may be missing")

            if not video_art:
                raise ValueError("No video or audio artifact found")

            # Curriculum duration & Logarithmic Budget Math
            curriculum = (await session.execute(select(Curriculum).where(Curriculum.id == curriculum_id))).scalar_one_or_none()
            video_duration = curriculum.duration if curriculum and curriculum.duration else 0

            duration_mins = video_duration / 60.0
            if duration_mins < 1:
                duration_mins = 1.0
            target_duration_mins = min(1.0 + 0.5 * math.log(duration_mins), 3.5)
            target_duration = target_duration_mins * 60.0

            total_word_budget = target_duration_mins * 140
            total_sentence_budget = int(total_word_budget / 14)
            logger.info(
                f"Target recap: {target_duration_mins:.2f} mins. Sentence Budget: {total_sentence_budget}"
            )

            # Concepts (still fetched, but used in LLM prompt)
            conc_stmt = select(Concept).where(Concept.curriculum_id == curriculum_id)
            concepts = (await session.execute(conc_stmt)).scalars().all()
            if not concepts:
                logger.warning("No concepts found, proceeding with LLM extraction anyway")

        s3 = get_s3_client()

        # Download video
        video_path = os.path.join(tmpdir, "source_video.mp4")
        try:
            s3.download_file(settings.s3.bucket, video_art.storage_uri, video_path)
        except Exception as e:
            raise ValueError(f"Failed to fetch video: {e}")

        # ---- Transcript handling ----
        transcript_path = os.path.join(tmpdir, "transcript.json")
        transcript_data = None

        if transcript_art:
            try:
                s3.download_file(settings.s3.bucket, transcript_art.storage_uri, transcript_path)
                with open(transcript_path, encoding="utf-8") as f:
                    transcript_data = json.load(f)
                logger.info("Loaded transcript from S3")
            except Exception as e:
                logger.warning(f"Failed to download transcript, will transcribe: {e}")
                transcript_data = None

        if transcript_data is None:
            logger.info("Transcribing audio on the fly")
            from ice_transcript import transcribe

            audio_tmp = os.path.join(tmpdir, "audio.wav")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-acodec",
                    "pcm_s16le",
                    audio_tmp,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            transcript_data = transcribe(audio_tmp)
            # Save for future
            with open(transcript_path, "w") as f:
                json.dump(transcript_data, f)
            s3_key = f"tenants/{tenant_id}/curricula/{curriculum_id}/transcript.json"
            s3.upload_file(
                transcript_path,
                settings.s3.bucket,
                s3_key,
                ExtraArgs={"ContentType": "application/json"},
            )
            if not transcript_art:
                async with factory() as session:
                    new_art = Artifact(
                        tenant_id=int(tenant_id),
                        curriculum_id=curriculum_id,
                        kind="transcript",
                        storage_uri=s3_key,
                        meta={"language": transcript_data.get("language", "en")},
                    )
                    session.add(new_art)
                    await session.commit()

        # ---- Extract sentences ----
        sentences = []
        segments = transcript_data.get("segments")
        if not segments:
            raise ValueError("No 'segments' in transcript")

        for seg in segments:
            start = seg.get("start")
            end = seg.get("end")
            text = seg.get("text", "").strip()
            if start is None or end is None or not text:
                continue

            words = seg.get("words")
            if (
                words
                and isinstance(words, list)
                and all(isinstance(w, dict) and "start" in w and "end" in w for w in words)
            ):
                # Word-level timestamps
                current_text = []
                start_time = words[0]["start"]
                for w in words:
                    wtext = w.get("word", "").strip()
                    current_text.append(wtext)
                    if wtext.endswith((".", "?", "!")):
                        end_time = w["end"]
                        sentences.append(
                            {
                                "text": " ".join(current_text),
                                "start": start_time,
                                "end": end_time,
                                "duration": end_time - start_time,
                            }
                        )
                        current_text = []
                        start_time = w["end"]
                if current_text:
                    sentences.append(
                        {
                            "text": " ".join(current_text),
                            "start": start_time,
                            "end": words[-1]["end"],
                            "duration": words[-1]["end"] - start_time,
                        }
                    )
            else:
                # Fallback: split by punctuation
                raw_sentences = re.split(r"(?<=[.!?])\s+", text)
                total_dur = end - start
                text_len = len(text)
                current_time = start
                for sent in raw_sentences:
                    if not sent:
                        continue
                    sent_len = len(sent)
                    duration_prop = sent_len / text_len if text_len > 0 else 0
                    sent_end = current_time + (total_dur * duration_prop)
                    sentences.append(
                        {
                            "text": sent,
                            "start": current_time,
                            "end": sent_end,
                            "duration": sent_end - current_time,
                        }
                    )
                    current_time = sent_end

        if not sentences:
            raise ValueError("No sentences extracted")

        # ---- LLM Embedding & scoring (Gemini) ----
        from ice_worker.tasks._gemini import get_gemini_model

        model = get_gemini_model(generation_config={"response_mime_type": "application/json"})

        concept_texts = "\n".join([f"- {c.label}: {c.description}" for c in concepts])

        prompt = f"""You are an expert video editor. I have a transcript of an educational video.
I need you to select the best sentences to create a summary recap.
Total Sentence Budget: {total_sentence_budget} sentences maximum.

Core Concepts to target:
{concept_texts}

Score each segment based on:
1. Concept Density (40%): introduces core definitions or logic.
2. Structural Signposts (30%): "Crucially", "The takeaway is", etc.
3. Code Relevance (20%): directly explains coding logic.
4. Acoustic Continuity (10%): complete thoughts without mid-phrase cuts.

Select the best segments that fit within the sentence budget.
Return a JSON object with EXACTLY this format (do not wrap in markdown blocks, just the JSON):
{{
  "summary": "A 2-3 sentence engaging summary of what this recap covers.",
  "segments": [
    {{"start": 12.5, "end": 24.0, "reason": "Introduces core definition"}}
  ]
}}

Here is the transcript data:
"""
        transcript_subset = [
            {"id": i, "start": s["start"], "end": s["end"], "text": s["text"]}
            for i, s in enumerate(sentences)
        ]
        transcript_json = json.dumps(transcript_subset)

        logger.info(f"Sending {len(transcript_subset)} sentences to Gemini")
        try:
            response = model.generate_content(prompt + transcript_json)
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            llm_result = json.loads(clean_text.strip())
            llm_summary = llm_result.get("summary", "Recap summary")
            llm_selected = llm_result.get("segments", [])
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError("LLM generation failed or returned invalid JSON")

        selected = []
        total_dur = 0.0
        for choice in llm_selected:
            start = float(choice["start"])
            end = float(choice["end"])
            dur = end - start
            if total_dur + dur > target_duration:
                break
            selected.append({"start": start, "end": end, "duration": dur})
            total_dur += dur

        selected.sort(key=lambda x: x["start"])
        selected = selected[: settings.recap_video.max_clips]

        if not selected:
            raise ValueError("No sentences selected for recap")

        # ---- Generate HTML Document ----
        html_output = ["<div class='transcript-container'>"]
        html_output.append(
            f"<div class='recap-summary'><h3 class='font-bold text-lg mb-2'>Summary</h3><p>{llm_summary}</p></div>"
        )
        html_output.append("<div class='recap-transcript'>")

        for segment in transcript_subset:
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            is_highlighted = False
            for chosen in selected:
                if start >= (chosen["start"] - 0.1) and end <= (chosen["end"] + 0.1):
                    is_highlighted = True
                    break

            if is_highlighted:
                html_output.append(
                    f"<mark class='recap-highlight' title='Included in Recap'>{text}</mark> "
                )
            else:
                html_output.append(f"<span>{text}</span> ")

        html_output.append("</div></div>")
        final_html = "".join(html_output)

        # Save HTML to database
        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import update
            await session.execute(update(Curriculum).where(Curriculum.id == curriculum_id).values(recap_transcript_html=final_html))
            await session.commit()

        # ---- FFmpeg extraction and stitching ----
        output_path = os.path.join(tmpdir, "recap.mp4")

        # Check if the source actually has a video track (since audio-only uploads are supported)
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            video_path,
        ]
        try:
            probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, text=True, check=True)
            probe_data = json.loads(probe_res.stdout)
            stream_types = {s.get("codec_type") for s in probe_data.get("streams", [])}
            has_video = "video" in stream_types
            has_audio = "audio" in stream_types
        except Exception as e:
            logger.warning(f"Failed to probe video streams: {e}. Defaulting to video with audio")
            has_video = True
            has_audio = True

        if not has_video and not has_audio:
            raise ValueError("Source artifact contains neither video nor audio")

        # Normalize one clip at a time so peak memory is independent of the
        # number of selected ranges. The final concat is a stream copy because
        # every intermediate has identical codecs and stream parameters.
        clip_paths = []
        for i, s in enumerate(selected):
            start_t = max(0, s["start"] - 0.2)
            dur = max(0.1, (s["end"] - s["start"]) + 0.4)
            clip_path = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
            clip_cmd = [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-ss",
                f"{start_t:.3f}",
                "-t",
                f"{dur:.3f}",
                "-i",
                video_path,
            ]

            if has_video:
                clip_cmd.extend(
                    [
                        "-vf",
                        (
                            f"scale={settings.recap_video.width}:{settings.recap_video.height}:"
                            "force_original_aspect_ratio=decrease,"
                            f"pad={settings.recap_video.width}:{settings.recap_video.height}:"
                            "(ow-iw)/2:(oh-ih)/2,"
                            f"fps={settings.recap_video.fps},format=yuv420p"
                        ),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-crf",
                        str(settings.recap_video.video_crf),
                        "-threads",
                        str(settings.recap_video.threads),
                    ]
                )

            if has_audio:
                clip_cmd.extend(
                    [
                        "-c:a",
                        "aac",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-b:a",
                        "96k",
                    ]
                )
            else:
                clip_cmd.append("-an")

            clip_cmd.extend(["-movflags", "+faststart", clip_path])
            logger.info(
                "Extracting recap clip %d/%d at %.3fs for %.3fs",
                i + 1,
                len(selected),
                start_t,
                dur,
            )
            try:
                subprocess.run(
                    clip_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error("FFmpeg clip %d failed with exit code %s: %s", i, e.returncode, e.stderr)
                raise RuntimeError(f"FFmpeg failed while extracting recap clip {i}") from e
            clip_paths.append(clip_path)

        concat_path = os.path.join(tmpdir, "concat.txt")
        with open(concat_path, "w", encoding="utf-8") as concat_file:
            for clip_path in clip_paths:
                concat_file.write(f"file '{clip_path}'\n")

        concat_cmd = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_path,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            output_path,
        ]
        logger.info(
            "Concatenating %d normalized recap clips (has_video=%s, has_audio=%s)",
            len(clip_paths),
            has_video,
            has_audio,
        )
        try:
            subprocess.run(
                concat_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error("FFmpeg concat failed with exit code %s: %s", e.returncode, e.stderr)
            raise RuntimeError("FFmpeg failed while concatenating recap clips") from e

        # ---- Upload to S3 ----
        s3_key = f"{tenant_prefix(tenant_id)}curricula/{curriculum_id}/recap.mp4"
        s3.upload_file(
            output_path, settings.s3.bucket, s3_key, ExtraArgs={"ContentType": "video/mp4"}
        )

        # ---- Generate presigned URL with external endpoint ----
        # Use environment variable for external MinIO URL (default to localhost:9000)
        # Build a simple public URL via the external endpoint.
        # The MinIO bucket has public-download policy so no presigned
        # signature is needed — avoids signature-invalidation when the
        # hostname changes (e.g. plain IP vs sslip.io proxy).
        external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000").rstrip("/")
        url = f"{external_endpoint}/{settings.s3.bucket}/{s3_key}"

        # Save to DB
        await _set_status(curriculum_id, tenant_id, "ready", url=url)


async def _run_with_failover(curriculum_id: str, tenant_id: str) -> None:
    try:
        await _run_recap(curriculum_id, tenant_id)
    except Exception as exc:
        logger.error(f"Recap generation failed: {exc}", exc_info=True)
        try:
            await _set_status(uuid.UUID(curriculum_id), tenant_id, "failed")
        except Exception:
            pass
        raise


@celery_app.task(
    name="ice_worker.tasks.recap.generate_recap",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=1,
)
def generate_recap(self: Any, curriculum_id: str, tenant_id: str) -> str:
    logger.info("generate_recap: cid=%s tenant=%s", curriculum_id, tenant_id)
    reset_engine()
    asyncio.run(_run_with_failover(curriculum_id, tenant_id))
    return curriculum_id
