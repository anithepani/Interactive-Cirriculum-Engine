"""yt-dlp download + ffmpeg audio extraction + MinIO upload (M1).

CPU-only / Windows-friendly. Downloads the audio-only stream from a YouTube
URL, converts it to a 16 kHz mono WAV (the canonical ASR input), uploads the
WAV to MinIO under a tenant-scoped key, and returns metadata for downstream
stages + DB persistence.

Validation (E22/E23): rejects videos outside the configured duration window
(``settings.pipeline.min/max_video_duration_sec``) before downloading.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yt_dlp
from ice_shared.s3 import get_s3_client, tenant_prefix
from ice_shared.settings import settings

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """Resolve an ffmpeg executable: PATH first, then the repo-root ffmpeg.exe."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    # Windows dev convenience: ffmpeg.exe ships at the repo root.
    repo_root = Path(__file__).resolve().parents[5]
    candidate = repo_root / "ffmpeg.exe"
    if candidate.exists():
        return str(candidate)
    # Fall back to the bare name; subprocess will raise a clear error if missing.
    return "ffmpeg"


def _probe(url: str) -> dict[str, Any]:
    """Fetch metadata without downloading; used for duration validation."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info or {}


def _download_media(url: str, out_dir: str) -> str:
    """Download the best video+audio stream; return the path to the downloaded file."""
    outtmpl = os.path.join(out_dir, "source.%(ext)s")
    opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": os.path.dirname(_find_ffmpeg()) or None,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    # yt-dlp picks the extension; find the downloaded file.
    files = [f for f in os.listdir(out_dir) if f.startswith("source.")]
    if not files:
        raise RuntimeError("yt-dlp produced no output file")
    return os.path.join(out_dir, files[0])


def _to_wav(src_path: str, wav_path: str) -> None:
    """Convert any audio file to 16 kHz mono PCM WAV via ffmpeg."""
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y", "-i", src_path,
        "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
        wav_path,
    ]
    logger.info("ffmpeg: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)


def _upload_wav(wav_path: str, tenant_id: Any, curriculum_id: Any) -> str:
    """Upload the WAV to MinIO under tenants/<tid>/curricula/<cid>/audio.wav."""
    s3 = get_s3_client()
    key = f"{tenant_prefix(tenant_id)}curricula/{curriculum_id}/audio.wav"
    bucket = settings.s3.bucket
    s3.upload_file(wav_path, bucket, key)
    logger.info("uploaded audio -> s3://%s/%s", bucket, key)
    return key


def ingest(
    video_ref: str,
    tenant_id: Any,
    curriculum_id: Any,
) -> dict[str, Any]:
    """Download + demux + WAV + upload. Returns metadata for M2 + DB.

    Returns:
        {"video_path": str, "audio_path": str, "s3_key": str, "title": str,
         "duration_sec": float, "language_hint": str}
    """
    info = _probe(video_ref)
    duration = float(info.get("duration") or 0)
    title = str(info.get("title") or "Untitled")
    language_hint = str(info.get("language") or "en")

    max_dur = settings.pipeline.max_video_duration_sec
    min_dur = settings.pipeline.min_video_duration_sec
    if duration and (duration < min_dur or duration > max_dur):
        raise ValueError(
            f"Video duration {duration:.0f}s outside allowed window "
            f"[{min_dur}, {max_dur}]s."
        )

    with tempfile.TemporaryDirectory(prefix="ice_ingest_") as tmp:
        src = _download_media(video_ref, tmp)
        wav_path = os.path.join(tmp, "audio.wav")
        _to_wav(src, wav_path)
        s3_key = _upload_wav(wav_path, tenant_id, curriculum_id)
        # M2 (faster-whisper) reads from a local path. Copy the WAV to a stable
        # temp path outside the context manager so it survives this call.
        stable_audio_name = os.path.join(
            tempfile.gettempdir(), f"ice_audio_{os.getpid()}.wav"
        )
        shutil.copy(wav_path, stable_audio_name)
        
        # M3 (vision) needs the video. Copy the source video too.
        ext = os.path.splitext(src)[1]
        stable_video_name = os.path.join(
            tempfile.gettempdir(), f"ice_video_{os.getpid()}{ext}"
        )
        shutil.copy(src, stable_video_name)

        logger.info("audio ready for ASR: %s", stable_audio_name)
        logger.info("video ready for Vision: %s", stable_video_name)
        return {
            "video_path": stable_video_name,
            "audio_path": stable_audio_name,
            "s3_key": s3_key,
            "title": title,
            "duration_sec": duration,
            "language_hint": language_hint,
        }
