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


def _ffprobe_duration(path: str) -> float:
    """Return the media duration in seconds via ffprobe (0.0 if unknown).

    Uses ffprobe from the same location as ffmpeg. Never raises — a probe
    failure just yields 0.0 so the pipeline continues (duration is only used
    for the validation window + UI display).
    """
    ffmpeg = _find_ffmpeg()
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if os.name == "nt" and not ffprobe.lower().endswith(".exe"):
        ffprobe += ".exe"
    if not (os.path.dirname(ffmpeg) and os.path.exists(ffprobe)):
        # Fall back to a bare `ffprobe` on PATH.
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float((out.stdout or "").strip() or 0.0)
    except (subprocess.CalledProcessError, ValueError, OSError) as exc:
        logger.info("ffprobe duration probe failed for %s: %s", path, exc)
        return 0.0


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


def _download_video(url: str, out_dir: str) -> str:
    """Download the best video+audio stream; return the path to the downloaded file."""
    outtmpl = os.path.join(out_dir, "source.%(ext)s")
    # Prefer H.264 (avc1) video: many YouTube streams default to AV1, which
    # fails to decode on CPU/WSL hardware ("Your platform doesn't support
    # hardware accelerated AV1 decoding" -> "Get current frame error"),
    # starving M3 vision/OCR of frames (and coding/debug exercises of code
    # context). The selector prefers avc1, then any non-AV1 mp4, then falls
    # back to the previous best-mp4/best chain so downloads never fail.
    opts = {
        "format": (
            "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[ext=mp4][vcodec!*=av01]+bestaudio[ext=m4a]/"
            "best[ext=mp4][vcodec!*=av01]/"
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ),
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


def _upload_video(video_path: str, tenant_id: Any, curriculum_id: Any) -> str:
    """Upload the source video to MinIO."""
    s3 = get_s3_client()
    ext = os.path.splitext(video_path)[1]
    key = f"{tenant_prefix(tenant_id)}curricula/{curriculum_id}/source_video{ext}"
    bucket = settings.s3.bucket
    s3.upload_file(video_path, bucket, key)
    logger.info("uploaded video -> s3://%s/%s", bucket, key)
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

    # Caption harvesting (Block F): try to reuse the video's existing subtitles
    # so the pipeline can skip Whisper ASR entirely. Never raises — returns None
    # when disabled/unavailable, in which case ASR runs as before.
    caption_transcript = None
    try:
        from ice_ingestion.captions import harvest_captions

        caption_transcript = harvest_captions(video_ref)
    except Exception as e:  # defensive: caption path must never break ingest
        logger.info("caption harvesting errored (%s); falling back to ASR", e)

    with tempfile.TemporaryDirectory(prefix="ice_ingest_") as tmp:
        src = _download_video(video_ref, tmp)
        wav_path = os.path.join(tmp, "audio.wav")
        _to_wav(src, wav_path)
        s3_key = _upload_wav(wav_path, tenant_id, curriculum_id)
        s3_video_key = _upload_video(src, tenant_id, curriculum_id)
        # M2 (faster-whisper) reads from a local path. Copy the WAV to a stable
        # temp path outside the context manager so it survives this call.
        stable_audio_name = os.path.join(
            tempfile.gettempdir(), f"ice_audio_{os.getpid()}.wav"
        )
        shutil.copy(wav_path, stable_audio_name)
        logger.info("audio ready for ASR: %s", stable_audio_name)

        # M3 (vision) needs the video. Copy the source video too.
        ext = os.path.splitext(src)[1]
        stable_video_name = os.path.join(
            tempfile.gettempdir(), f"ice_video_{os.getpid()}{ext}"
        )
        shutil.copy(src, stable_video_name)
        logger.info("video ready for Vision: %s", stable_video_name)
        return {
            "video_path": stable_video_name,
            "audio_path": stable_audio_name,
            "s3_key": s3_key,
            "s3_video_key": s3_video_key,
            "title": title,
            "duration_sec": duration,
            "language_hint": language_hint,
            # Non-None when existing YouTube captions were harvested; the worker
            # uses this to skip Whisper ASR. Canonical transcript contract.
            "caption_transcript": caption_transcript,
        }


def _download_object(s3_key: str, dest_path: str) -> None:
    """Download an object from MinIO/S3 to a local path."""
    s3 = get_s3_client()
    bucket = settings.s3.bucket
    s3.download_file(bucket, s3_key, dest_path)
    logger.info("downloaded upload -> %s (from s3://%s/%s)", dest_path, bucket, s3_key)


def ingest_upload(
    s3_key: str,
    tenant_id: Any,
    curriculum_id: Any,
) -> dict[str, Any]:
    """Ingest a previously-uploaded local video already stored in MinIO.

    The API's ``POST /curricula/upload`` endpoint streams the raw upload to
    ``tenants/<tid>/curricula/<cid>/source_video<ext>`` and stores that S3 key
    as the curriculum's ``source_ref``. This function pulls that object back
    down to a local temp path, extracts a 16 kHz mono WAV via the existing
    ``_to_wav`` helper, probes duration with ffprobe, and returns the SAME
    contract dict as :func:`ingest` so the rest of the pipeline (M2..M8) is
    entirely source-agnostic.

    Unlike the YouTube path there are no captions, so ``caption_transcript`` is
    ``None`` — the worker falls through to Whisper ASR. The uploaded source
    object is intentionally left in MinIO (not deleted) so the HTML5 player can
    stream it later; only the local temp copies are cleaned up by the worker.

    Returns:
        {"video_path": str, "audio_path": str, "s3_key": str,
         "s3_video_key": str, "title": str, "duration_sec": float,
         "language_hint": str, "caption_transcript": None}
    """
    ext = os.path.splitext(s3_key)[1] or ".mp4"
    # Derive a human-ish title from the stored key (endpoint may override the
    # curriculum title separately; this is a safe fallback).
    title = os.path.splitext(os.path.basename(s3_key))[0] or "Uploaded video"

    with tempfile.TemporaryDirectory(prefix="ice_upload_") as tmp:
        src = os.path.join(tmp, f"source{ext}")
        _download_object(s3_key, src)

        duration = _ffprobe_duration(src)
        max_dur = settings.pipeline.max_video_duration_sec
        min_dur = settings.pipeline.min_video_duration_sec
        if duration and (duration < min_dur or duration > max_dur):
            raise ValueError(
                f"Video duration {duration:.0f}s outside allowed window "
                f"[{min_dur}, {max_dur}]s."
            )

        wav_path = os.path.join(tmp, "audio.wav")
        _to_wav(src, wav_path)
        audio_s3_key = _upload_wav(wav_path, tenant_id, curriculum_id)

        # Stable copies outside the context manager (survive this call) for M2/M3.
        stable_audio_name = os.path.join(
            tempfile.gettempdir(), f"ice_audio_{os.getpid()}.wav"
        )
        shutil.copy(wav_path, stable_audio_name)
        logger.info("audio ready for ASR: %s", stable_audio_name)

        stable_video_name = os.path.join(
            tempfile.gettempdir(), f"ice_video_{os.getpid()}{ext}"
        )
        shutil.copy(src, stable_video_name)
        logger.info("video ready for Vision: %s", stable_video_name)

        return {
            "video_path": stable_video_name,
            "audio_path": stable_audio_name,
            "s3_key": audio_s3_key,
            # The uploaded source video already lives at this key in MinIO.
            "s3_video_key": s3_key,
            "title": title,
            "duration_sec": duration,
            "language_hint": "en",
            # No captions on uploads → worker runs Whisper ASR.
            "caption_transcript": None,
        }
