# M1 - Ingestion Pipeline

Takes a YouTube URL or uploaded file (`+ tenant_id`) and produces local artifacts:
video file, 16 kHz mono WAV audio, sampled frames (1 fps + shot-change frames), and
metadata (duration, language hint). Emits `artifact_path + manifest` to the Celery queue.

## Tech
- **yt-dlp** - download, handles private/age-restricted/deleted errors gracefully
- **ffmpeg/ffprobe** - demux, audio extract, validate codec, frame sample
- **PySceneDetect** - shot boundary detection
- **OpenCV** - frame sampling + resize for OCR

## Validation (master plan risks E22-E24, E35)
- Reject files >4h or <30s (`PIPELINE_MAX_VIDEO_DURATION_SEC` / `MIN_VIDEO_DURATION_SEC`)
- Reject unsupported codecs (ffprobe pre-check)
- Dedupe by content hash (video ID + transcript hash)
- Clear user-facing error + retry guidance for private/age-restricted/deleted YT URLs

## Interface (§5.3)
Emits `artifact_path + manifest` to the Celery queue; consumed by M2 (transcript) and M3 (vision).

## Owner
**Lead:** Zubair · **Support:** Ahmed
