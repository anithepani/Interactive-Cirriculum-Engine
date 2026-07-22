import asyncio
import json
import logging
import os
import subprocess
import tempfile
import math
import requests
from typing import Any

from ice_shared import settings
from ice_shared.db import get_session_factory, get_engine, reset_engine, set_tenant_context, Base
from ice_shared.s3 import get_s3_client, tenant_prefix
from ice_api.models import Curriculum, Concept, Artifact
from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

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
            c.signal_status = status
            if url:
                c.signal_video_url = url
            await session.commit()

def get_audio_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

def fetch_pexels_broll(keywords: str) -> str | None:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        logger.warning("PEXELS_API_KEY not found in environment.")
        return None
    
    url = f"https://api.pexels.com/videos/search?query={keywords}&per_page=1&orientation=landscape&size=medium"
    headers = {"Authorization": api_key}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            # fallback query
            resp = requests.get(f"https://api.pexels.com/videos/search?query=technology&per_page=1&orientation=landscape", headers=headers, timeout=10)
            data = resp.json()
            videos = data.get("videos", [])
            
        if videos:
            video_files = videos[0].get("video_files", [])
            # Try to get an HD version or just the first
            for vf in video_files:
                if vf.get("quality") == "hd":
                    return vf.get("link")
            if video_files:
                return video_files[0].get("link")
    except Exception as e:
        logger.error(f"Error fetching from Pexels: {e}")
    return None

def create_ass_subtitle(text: str, duration: float, out_path: str):
    # Split text into chunks if it's too long
    # But for a simple subtitle, we'll just write one line
    # A simple ASS file template
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

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
    curriculum_id = int(curriculum_id_str)
    set_tenant_context(tenant_id)
    await _ensure_tables()
    await _set_status(curriculum_id, tenant_id, "processing")
    
    factory = get_session_factory()
    async with factory() as session:
        curriculum = await session.get(Curriculum, curriculum_id)
        if not curriculum:
            raise ValueError(f"Curriculum {curriculum_id} not found")
        
        target_duration = min(1 + 0.5 * math.log(max(1, curriculum.duration or 3600) / 60.0), 3.5) * 60
        # ~130 words per min = max words
        max_words = int((target_duration / 60) * 130)

        # load transcript
        from sqlalchemy import select
        stmt = select(Artifact).where(Artifact.curriculum_id == curriculum_id, Artifact.kind == "transcript")
        res = await session.execute(stmt)
        transcript_art = res.scalars().first()

    if not transcript_art:
        await _set_status(curriculum_id, tenant_id, "failed")
        raise ValueError("Transcript not found")

    s3 = get_s3_client()
    with tempfile.TemporaryDirectory() as tmpdir:
        transcript_path = os.path.join(tmpdir, "transcript.json")
        s3.download_file(settings.s3.bucket, transcript_art.storage_uri, transcript_path)
        with open(transcript_path, "r") as f:
            transcript_data = json.load(f)
            
        sentences = []
        for seg in transcript_data.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                sentences.append(text)
        
        full_text = " ".join(sentences)
        
        worker_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        apps_dir = os.path.dirname(worker_dir)
        remotion_dir = os.path.join(apps_dir, "remotion")
        
        # Call Gemini (dynamic model selection w/ fallback — shared with recap).
        # Hardcoding the model name silently broke this task when the name was
        # not served; list_models() + fallback makes failures loud.
        from ice_worker.tasks._gemini import get_gemini_model
        model = get_gemini_model(generation_config={"response_mime_type": "application/json"})
        
        prompt = f"""You are an expert documentary producer and technical educator. I have a transcript of an educational video.
I need you to select the highest-signal, most important sentences to create a summary.
The total selected text must NOT exceed {max_words} words.

For each core sentence, you must also provide:
1. `theme`: A mood/theme for the background that matches the situation of the sentence. Must be one of: "tech", "warning", "success", "creative", "dark", "neon", "nature", "academic".
2. `codeSnippet`: (Optional) If the sentence is explicitly discussing code, programming, or an algorithm, provide the EXACT code snippet it references. If not about code, omit this field or leave it empty.
3. `codeLanguage`: (Optional) The programming language of the snippet (e.g., "python", "javascript", "bash").

Return a JSON array of EXACTLY this format:
[
  {{
    "sentence": "A for loop lets you iterate over a range of numbers.", 
    "theme": "tech",
    "codeSnippet": "for i in range(10):\\n    print(i)",
    "codeLanguage": "python"
  }},
  {{
    "sentence": "However, infinite loops will crash your program!",
    "theme": "warning"
  }}
]

Transcript:
{full_text[:50000]} # Truncated for safety
"""
        logger.info(f"Sending prompt to Gemini for signal video (Max words: {max_words})")
        resp = model.generate_content(prompt)
        try:
            clean_text = resp.text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            segments = json.loads(clean_text)
        except Exception as e:
            logger.error(f"Gemini failed: {e}")
            await _set_status(curriculum_id, tenant_id, "failed")
            return
            
        slides_data = []
        
        for idx, seg in enumerate(segments):
            sentence = seg.get("sentence", "").strip()
            if not sentence: continue
            
            # 1. Edge-TTS Audio
            audio_filename = f"audio_{curriculum_id}_{idx}.mp3"
            audio_path = os.path.join(remotion_dir, "public", "tmp_audio", audio_filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            
            cmd_tts = ["edge-tts", "--voice", "en-US-ChristopherNeural", "--text", sentence, "--write-media", audio_path]
            subprocess.run(cmd_tts, check=True)
            
            audio_dur = get_audio_duration(audio_path)
            if audio_dur <= 0:
                continue
                
            slides_data.append({
                "text": sentence,
                "durationInFrames": int(math.ceil(audio_dur * 30)),
                "audioPath": f"tmp_audio/{audio_filename}",
                "theme": seg.get("theme", "dark"),
                "codeSnippet": seg.get("codeSnippet"),
                "codeLanguage": seg.get("codeLanguage")
            })
            
        if not slides_data:
            await _set_status(curriculum_id, tenant_id, "failed")
            return
            
        # Write props for remotion
        props_path = os.path.join(tmpdir, "props.json")
        with open(props_path, "w") as f_props:
            json.dump({"slides": slides_data}, f_props)
            
        final_video_path = os.path.join(tmpdir, "signal_video.mp4")
        
        # 4. Run remotion render (failures must surface a status + full log)
        render_cmd = [
            "npx", "remotion", "render", "src/index.ts", "MainComp", final_video_path,
            "--props", props_path
        ]
        
        render_cmd_str = " ".join(render_cmd)
        logger.info(f"Rendering Remotion video... {render_cmd_str}")
        try:
            # When using shell=True, pass the command as a single string
            res_render = subprocess.run(render_cmd_str, cwd=remotion_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if res_render.returncode != 0:
                logger.error(f"Remotion render error: {res_render.stderr}\n{res_render.stdout}")
        except Exception as render_exc:
            logger.error(f"Remotion render subprocess failed: {render_exc}", exc_info=True)
            await _set_status(curriculum_id, tenant_id, "failed")
            return
        
        if not os.path.exists(final_video_path):
            logger.error("Remotion render produced no output file at %s", final_video_path)
            await _set_status(curriculum_id, tenant_id, "failed")
            return
            
        # 5. Upload to S3
        s3_key = f"tenants/{tenant_id}/curricula/{curriculum_id}/signal_video.mp4"
        s3.upload_file(final_video_path, settings.s3.bucket, s3_key, ExtraArgs={'ContentType': 'video/mp4'})
        
        async with factory() as session:
            c = await session.get(Curriculum, curriculum_id)
            if c:
                new_art = Artifact(
                    tenant_id=int(tenant_id),
                    curriculum_id=curriculum_id,
                    kind="signal_video",
                    storage_uri=s3_key
                )
                session.add(new_art)
                await session.commit()
                
        presigned = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.s3.bucket, 'Key': s3_key},
            ExpiresIn=3600*24*7
        )
        
        # Generate a browser-valid presigned URL via an external-facing MinIO
        # client (mirrors recap.py). String-replacing the internal minio:9000
        # host can invalidate the S3 signature; signing against the external
        # endpoint avoids that entirely.
        import boto3
        from botocore.config import Config

        external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000")
        external_s3 = boto3.client(
            's3',
            endpoint_url=external_endpoint,
            aws_access_key_id=settings.s3.access_key,
            aws_secret_access_key=settings.s3.secret_key,
            config=Config(signature_version='s3v4'),
            region_name=settings.s3.region,
        )
        presigned = external_s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.s3.bucket, 'Key': s3_key},
            ExpiresIn=7 * 24 * 3600,
        )
        
        await _set_status(curriculum_id, tenant_id, "ready", presigned)

async def _run_with_failover(curriculum_id: str, tenant_id: str) -> None:
    try:
        await _run_signal_video(curriculum_id, tenant_id)
    except Exception as exc:
        logger.error(f"Signal video generation failed: {exc}", exc_info=True)
        try:
            await _set_status(int(curriculum_id), tenant_id, "failed")
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
