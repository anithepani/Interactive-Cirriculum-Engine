"""Video ingestion + processing pipeline dispatch (API side).

Dispatches the real AI pipeline to the Celery worker via ``send_task`` (decoupled
-- the API process never imports ice_worker, keeping yt-dlp / Celery / the AI
libs out of the API). The task ``ice_worker.tasks.generate_curriculum.generate_curriculum``
runs the full M1->M8 sequence and persists results; the API returns immediately
with the curriculum row already in ``queued`` status.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import Celery
from ice_shared import settings

logger = logging.getLogger(__name__)

# Send-only Celery instance: just enough to enqueue a task on the broker.
# Importing ice_worker here would drag the entire AI stack into the API process.
_send_celery: Celery | None = None


def _get_sender() -> Celery:
    global _send_celery
    if _send_celery is None:
        _send_celery = Celery(
            "ice",
            broker=settings.celery.broker_url,
            backend=settings.celery.result_backend,
        )
        _send_celery.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
        )
    return _send_celery


async def process_video(
    curriculum_id: Any, video_ref: str, tenant_id: Any
) -> None:
    """Dispatch curriculum generation to the Celery worker.

    Args:
        curriculum_id: id of the freshly-created Curriculum row.
        video_ref: the YouTube URL (or file ref) to process.
        tenant_id: owning tenant id (for RLS + S3 scoping).
    """
    try:
        _get_sender().send_task(
            "ice_worker.tasks.generate_curriculum.generate_curriculum",
            args=[str(curriculum_id), str(video_ref), str(tenant_id)],
        )
        logger.info(
            "dispatched generate_curriculum: cid=%s video=%s tenant=%s",
            curriculum_id, video_ref, tenant_id,
        )
    except Exception:
        # Surface the error but don't crash the request.
        logger.exception("failed to dispatch generate_curriculum task")


async def trigger_recap(
    curriculum_id: Any, tenant_id: Any
) -> None:
    """Dispatch recap generation to the Celery worker.

    Args:
        curriculum_id: id of the Curriculum row.
        tenant_id: owning tenant id (for RLS + S3 scoping).
    """
    try:
        _get_sender().send_task(
            "ice_worker.tasks.recap.generate_recap",
            args=[str(curriculum_id), str(tenant_id)],
        )
        logger.info(
            "dispatched generate_recap: cid=%s tenant=%s",
            curriculum_id, tenant_id,
        )
    except Exception:
        logger.exception("failed to dispatch generate_recap task")

async def trigger_signal(
    curriculum_id: Any, tenant_id: Any
) -> None:
    """Dispatch signal video generation to the Celery worker."""
    try:
        _get_sender().send_task(
            "ice.worker.generate_signal_video",
            args=[str(curriculum_id), str(tenant_id)],
        )
        logger.info(
            "dispatched generate_signal_video: cid=%s tenant=%s",
            curriculum_id, tenant_id,
        )
    except Exception:
        logger.exception("failed to dispatch generate_signal_video task")
