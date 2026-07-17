"""recap.py: Celery task to generate a 5-minute video recap.

This task takes an existing curriculum, fetches the video and transcript,
extracts the top ~300s of sentences by matching their embeddings against
the concept graph, and concatenates them using FFmpeg.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

from sentence_transformers import SentenceTransformer

from ice_shared import settings
from ice_shared.db import get_session_factory, get_engine, reset_engine, set_tenant_context, Base
from ice_shared.s3 import get_s3_client, tenant_prefix
from ice_api.models import Curriculum, Concept, Artifact
from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Windows asyncio fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_embedder: SentenceTransformer | None = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info("Loading sentence-transformers all-MiniLM-L6-v2")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


async def _ensure_tables() -> None:
    import ice_api.models  # noqa: F401
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _set_status(curriculum_id: int, tenant_id: str, status: str, url: str | None = None) -> None:
    set_tenant_context(tenant_id)
    factory = get_session_factory()
    async with factory() as session:
        c = await session.get(Curriculum, curriculum_id)
        if c:
            c.recap_status = status
            if url:
                c.recap_url = url
            await session.commit()


async def _run_recap(curriculum_id_str: str, tenant_id: str) -> None:
    curriculum_id = int(curriculum_id_str)
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

            # Curriculum duration
            curriculum = await session.get(Curriculum, curriculum_id)
            video_duration = curriculum.duration if curriculum and curriculum.duration else 0
            target_duration = min(300, max(60, video_duration * 0.7))
            logger.info(f"Target recap duration: {target_duration:.1f}s")

            # Concepts
            conc_stmt = select(Concept).where(Concept.curriculum_id == curriculum_id)
            concepts = (await session.execute(conc_stmt)).scalars().all()
            if not concepts:
                raise ValueError("No concepts found")

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
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                logger.info("Loaded transcript from S3")
            except Exception as e:
                logger.warning(f"Failed to download transcript, will transcribe: {e}")
                transcript_data = None

        if transcript_data is None:
            logger.info("Transcribing audio on the fly")
            from ice_transcript import transcribe
            audio_tmp = os.path.join(tmpdir, "audio.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path,
                "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
                audio_tmp
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            transcript_data = transcribe(audio_tmp)
            # Save for future
            with open(transcript_path, "w") as f:
                json.dump(transcript_data, f)
            s3_key = f"tenants/{tenant_id}/curricula/{curriculum_id}/transcript.json"
            s3.upload_file(transcript_path, settings.s3.bucket, s3_key, ExtraArgs={'ContentType': 'application/json'})
            if not transcript_art:
                async with factory() as session:
                    new_art = Artifact(
                        tenant_id=int(tenant_id),
                        curriculum_id=curriculum_id,
                        kind="transcript",
                        storage_uri=s3_key,
                        meta={"language": transcript_data.get("language", "en")}
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
            if not start or not end or not text:
                continue

            words = seg.get("words")
            if words and isinstance(words, list) and all(isinstance(w, dict) and "start" in w and "end" in w for w in words):
                # Word-level timestamps
                current_text = []
                start_time = words[0]["start"]
                for w in words:
                    wtext = w.get("word", "").strip()
                    current_text.append(wtext)
                    if wtext.endswith((".", "?", "!")):
                        end_time = w["end"]
                        sentences.append({
                            "text": " ".join(current_text),
                            "start": start_time,
                            "end": end_time,
                            "duration": end_time - start_time
                        })
                        current_text = []
                        start_time = w["end"]
                if current_text:
                    sentences.append({
                        "text": " ".join(current_text),
                        "start": start_time,
                        "end": words[-1]["end"],
                        "duration": words[-1]["end"] - start_time
                    })
            else:
                # Fallback: split by punctuation
                raw_sentences = re.split(r'(?<=[.!?])\s+', text)
                total_dur = end - start
                text_len = len(text)
                current_time = start
                for sent in raw_sentences:
                    if not sent:
                        continue
                    sent_len = len(sent)
                    duration_prop = sent_len / text_len if text_len > 0 else 0
                    sent_end = current_time + (total_dur * duration_prop)
                    sentences.append({
                        "text": sent,
                        "start": current_time,
                        "end": sent_end,
                        "duration": sent_end - current_time
                    })
                    current_time = sent_end

        if not sentences:
            raise ValueError("No sentences extracted")

        # ---- Embedding & scoring ----
        embedder = _get_embedder()
        concept_texts = [c.label + " " + (c.description or "") for c in concepts]
        concept_embeddings = embedder.encode(concept_texts, convert_to_tensor=True)

        sentence_texts = [s["text"] for s in sentences]
        sentence_embeddings = embedder.encode(sentence_texts, convert_to_tensor=True)

        from sentence_transformers.util import cos_sim
        similarities = cos_sim(sentence_embeddings, concept_embeddings)
        max_sims = similarities.max(dim=1).values.tolist()
        for idx, score in enumerate(max_sims):
            sentences[idx]["score"] = score

        # Greedy selection up to target_duration
        sentences_sorted_by_score = sorted(sentences, key=lambda x: x["score"], reverse=True)
        selected = []
        total_dur = 0.0
        for s in sentences_sorted_by_score:
            if total_dur + s["duration"] > target_duration:
                break
            selected.append(s)
            total_dur += s["duration"]

        selected.sort(key=lambda x: x["start"])

        if not selected:
            raise ValueError("No sentences selected for recap")
            
        if total_dur < 30.0:
            logger.warning(f"Selected recap duration ({total_dur:.1f}s) is shorter than 30s")

        # ---- FFmpeg extraction ----
        concat_list_path = os.path.join(tmpdir, "concat.txt")
        clips = []

        for i, s in enumerate(selected):
            clip_path = os.path.join(tmpdir, f"clip_{i}.mp4")
            start_t = max(0, s["start"] - 0.2)
            dur = (s["end"] - s["start"]) + 0.4

            cmd = [
                "ffmpeg", "-y", "-ss", str(start_t), "-i", video_path,
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k",
                "-avoid_negative_ts", "make_zero",
                clip_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            clips.append(clip_path)

        with open(concat_list_path, "w", encoding="utf-8") as f:
            for c in clips:
                f.write(f"file '{os.path.basename(c)}'\n")

        output_path = os.path.join(tmpdir, "recap.mp4")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", output_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # ---- Upload to S3 ----
        s3_key = f"{tenant_prefix(tenant_id)}curricula/{curriculum_id}/recap.mp4"
        s3.upload_file(output_path, settings.s3.bucket, s3_key, ExtraArgs={'ContentType': 'video/mp4'})

        # ---- Generate presigned URL with external endpoint ----
        # Use environment variable for external MinIO URL (default to localhost:9000)
        external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000")
        # Extract the bucket and key, build URL manually
        # Note: we need to sign the URL properly; easiest is to use boto3 client with a custom endpoint.
        # We'll override the client's endpoint for this one call.

        # Create a new client with the external endpoint
        import boto3
        from botocore.config import Config

        external_s3 = boto3.client(
            's3',
            endpoint_url=external_endpoint,
            aws_access_key_id=settings.s3.access_key,
            aws_secret_access_key=settings.s3.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'  # adjust if needed
        )
        url = external_s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.s3.bucket, 'Key': s3_key},
            ExpiresIn=7 * 24 * 3600
        )

        # Save to DB
        await _set_status(curriculum_id, tenant_id, "ready", url=url)


async def _run_with_failover(curriculum_id: str, tenant_id: str) -> None:
    try:
        await _run_recap(curriculum_id, tenant_id)
    except Exception as exc:
        logger.error(f"Recap generation failed: {exc}", exc_info=True)
        try:
            await _set_status(int(curriculum_id), tenant_id, "failed")
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