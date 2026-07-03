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

from pathlib import Path
from uuid import UUID


def ingest_video(video_ref: str, tenant_id: UUID) -> Path:
    """Download/upload + demux + audio extract + frame sample.

    Returns the local artifact directory. Raises on invalid input.
    Phase 1 (weeks 2-3) deliverable.
    """
    raise NotImplementedError("Phase 1 deliverable - see libs/ai/ingestion/README.md")
