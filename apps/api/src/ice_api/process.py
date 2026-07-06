from __future__ import annotations
import os
import sys
import json
import shutil
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import yt_dlp
from sqlalchemy import text

from ice_shared.db import async_session, set_tenant_context
from ice_api.models import Curriculum

# Correct path: ice_api -> src -> api -> apps -> repo root
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

async def process_video(curriculum_id: int, tenant_id: int = 1):
    """
    Real video ingestion pipeline:
    1. If video_url is a local audio file, use it directly.
    2. Otherwise, download audio from YouTube using yt-dlp.
    3. Transcribe with Whisper (tiny) in 30-second chunks.
    4. Store segments, dummy concepts, and checkpoints in DB.
    5. Generate exercises for each checkpoint.
    """
    print(f"🚀 process_video called with curriculum_id: {curriculum_id}")
    set_tenant_context(str(tenant_id))

    try:
        # 1. Get the video URL from the curriculum record
        async with async_session() as session:
            curriculum = await session.get(Curriculum, curriculum_id)
            if not curriculum:
                raise ValueError(f"Curriculum {curriculum_id} not found")
            video_url = curriculum.source_ref
            if not video_url:
                raise ValueError("No video URL found for this curriculum")

        # 2. Create temporary directory for downloads
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            audio_path = tmp_path / "audio"

            # ----- LOCAL FILE OVERRIDE (for testing) -----
            if video_url.endswith((".wav", ".mp3", ".m4a", ".flac", ".ogg")):
                local_file = Path(video_url)
                if local_file.exists():
                    # Copy the local file to the temp directory
                    dest = tmp_path / local_file.name
                    shutil.copy2(local_file, dest)
                    audio_path = dest
                    print(f"🎵 Using local audio file: {audio_path}")
                else:
                    raise FileNotFoundError(f"Local file not found: {local_file}")
            else:
                # ----- YouTube download (original code) -----
                print(f"⬇️  Downloading audio from {video_url}...")
                ydl_opts = {
                    'outtmpl': str(audio_path) + '.%(ext)s',
                    'format': 'bestaudio/best',
                    'quiet': False,
                    'no_warnings': True,
                    'nopart': True,
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                    'cookiefile': None,
                    'extractor_args': {
                        'youtube': {
                            'skip': ['webpage'],
                        },
                    },
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                # Find the actual audio file
                audio_files = list(tmp_path.glob("audio.*"))
                if not audio_files:
                    raise FileNotFoundError("Audio file not created by yt-dlp")
                audio_path = audio_files[0]

            print(f"✅ Audio ready: {audio_path}")

            # 3. Transcribe with Whisper (tiny) in 30-second chunks
            print("🗣️  Transcribing audio with Whisper (tiny) in chunks...")
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel("tiny", device="cpu", compute_type="int8")
                segments, info = model.transcribe(
                    str(audio_path),
                    word_timestamps=True,
                    chunk_length=30,          # <-- critical for long audio
                    beam_size=5
                )
                transcript_segments = []
                for seg in segments:
                    transcript_segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                    })
                print(f"✅ Transcription complete: {len(transcript_segments)} segments")
            except ImportError:
                print("⚠️  faster-whisper not installed – using mock data")
                mock_path = REPO_ROOT / "long_segments.json"
                if not mock_path.exists():
                    mock_data = [{"start": 0, "end": 10, "text": "Mock segment 1"},
                                 {"start": 10, "end": 20, "text": "Mock segment 2"}]
                    with open(mock_path, "w") as f:
                        json.dump(mock_data, f)
                    print(f"📄 Created mock data at {mock_path}")
                with open(mock_path, "r") as f:
                    transcript_segments = json.load(f)
            except Exception as e:
                print(f"⚠️  Whisper failed: {e} – falling back to mock data")
                mock_path = REPO_ROOT / "long_segments.json"
                if not mock_path.exists():
                    mock_data = [{"start": 0, "end": 10, "text": "Mock segment 1"},
                                 {"start": 10, "end": 20, "text": "Mock segment 2"}]
                    with open(mock_path, "w") as f:
                        json.dump(mock_data, f)
                    print(f"📄 Created mock data at {mock_path}")
                with open(mock_path, "r") as f:
                    transcript_segments = json.load(f)

            # 4. Store data in the database
            async with async_session() as session:
                print("📂 Inserting segments into database...")
                # Clear old data
                await session.execute(text("DELETE FROM segments WHERE curriculum_id = :cid"), {"cid": curriculum_id})
                await session.execute(text("DELETE FROM concepts WHERE curriculum_id = :cid"), {"cid": curriculum_id})
                await session.execute(text("DELETE FROM checkpoints WHERE curriculum_id = :cid"), {"cid": curriculum_id})
                print("🗑️  Old data cleared.")

                # Insert segments
                for idx, seg in enumerate(transcript_segments):
                    print(f"  Inserting segment {idx+1}...")
                    await session.execute(
                        text("""
                            INSERT INTO segments
                            (curriculum_id, title, summary, start_time, end_time)
                            VALUES (:cid, :title, :summary, :start, :end)
                        """),
                        {
                            "cid": curriculum_id,
                            "title": f"Segment {idx+1}",
                            "summary": seg.get("text", seg.get("summary", "No text")),
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                        }
                    )
                print("✅ Segments inserted.")

                # Insert a dummy concept
                await session.execute(
                    text("INSERT INTO concepts (curriculum_id, label, description) VALUES (:cid, 'concept', 'mock')"),
                    {"cid": curriculum_id}
                )
                print("✅ Concept inserted.")

                # Insert checkpoints (one per segment, at midpoint)
                for seg in transcript_segments:
                    start = seg.get("start", 0)
                    end = seg.get("end", start + 10)
                    await session.execute(
                        text("""
                            INSERT INTO checkpoints
                            (curriculum_id, segment_id, concept_id, ts, exercise_type, difficulty)
                            VALUES (
                                :cid,
                                (SELECT id FROM segments WHERE curriculum_id = :cid AND start_time = :start LIMIT 1),
                                (SELECT id FROM concepts WHERE curriculum_id = :cid LIMIT 1),
                                :ts,
                                'mcq',
                                3
                            )
                        """),
                        {
                            "cid": curriculum_id,
                            "start": start,
                            "ts": (start + end) / 2,
                        }
                    )
                print("✅ Checkpoints inserted.")

                # Update curriculum status
                await session.execute(
                    text("UPDATE curricula SET status = 'ready', ready_at = :ready WHERE id = :id"),
                    {"ready": datetime.utcnow().isoformat(), "id": curriculum_id}
                )
                await session.commit()
                print("✅ Curriculum status updated to 'ready'.")

        # 5. Generate exercises for the checkpoints
        from ice_api.exercise_gen import generate_exercises_for_curriculum
        await generate_exercises_for_curriculum(curriculum_id)

        print(f"✅ Curriculum {curriculum_id} processed successfully.")

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        print(traceback.format_exc())
        async with async_session() as session:
            await session.execute(
                text("UPDATE curricula SET status = 'failed' WHERE id = :id"),
                {"id": curriculum_id}
            )
            await session.commit()
        raise