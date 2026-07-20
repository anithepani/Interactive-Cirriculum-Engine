"""M1 Ingestion Pipeline.

Takes a YouTube URL or uploaded file (+ tenant_id) and produces:
- local video file
- audio track (16 kHz mono WAV)
- sampled frames (1 fps + shot-change frames via PySceneDetect)
- metadata (duration, language hint)

Tech: yt-dlp, ffmpeg/ffprobe, PySceneDetect, OpenCV.
Emits artifact_path + manifest to the Celery queue.

Validation (E22, E23, E24, E35): reject >4h / <30s; reject unsupported codecs;
dedupe by content hash; handle private/age-restricted/deleted URLs gracefully.

Lead: Zubair. Support: Ahmed (vision fusion).
"""
from __future__ import annotations

from typing import Any


def ingest_video(
    video_ref: str, tenant_id: Any, curriculum_id: Any = None
) -> dict:
    """Download/upload + demux + audio extract.

    Args:
        video_ref: YouTube URL (or local file path) to ingest.
        tenant_id: Owning tenant (int under the ORM schema; UUID under the
            deferred Postgres migration). Used for S3 key scoping + RLS.
        curriculum_id: Curriculum row id (for the S3 key path).

    Returns:
        ``{"video_path": str, "audio_path": str, "s3_key": str, "title": str,
        "duration_sec": float, "language_hint": str}`` -- the local WAV path
        feeds M2 (transcribe); the video feeds M3 (vision); the rest persists to the DB.

    Raises:
        ValueError: if the video duration is outside the configured window.
        RuntimeError: if yt-dlp / ffmpeg fail.
    """
    from ice_ingestion.downloader import ingest

    return ingest(video_ref, tenant_id, curriculum_id)


__all__ = ["ingest_video"]

