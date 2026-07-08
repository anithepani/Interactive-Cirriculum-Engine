"""Video ingestion + processing pipeline entrypoint.

Phase-1 stub: flips the curriculum status to ``processing`` then ``ready``
without running the real AI pipeline. The real pipeline (calling
ice_ingestion -> ice_transcript -> ice_segmentation -> ice_concept_graph ->
ice_checkpoints via the Celery worker) lands in Phase 2-3.

The previous inline implementation (faster-whisper + raw SQL against renamed
columns) was removed because it bypassed the AI libs and used a divergent
schema.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from ice_shared import get_session_factory, set_tenant_context
from ice_api.models import Curriculum

logger = logging.getLogger(__name__)


async def process_video(curriculum_id: str, tenant_id: str) -> None:
    """Stub: mark the curriculum ready without running the AI pipeline.

    Args:
        curriculum_id: str UUID of the curriculum row.
        tenant_id: str UUID of the owning tenant (for RLS).
    """
    set_tenant_context(tenant_id)
    factory = get_session_factory()
    async with factory() as session:
        curriculum = await session.get(Curriculum, UUID(curriculum_id))
        if not curriculum:
            logger.error(f"process_video: curriculum {curriculum_id} not found")
            return

        curriculum.status = "processing"
        await session.commit()

        # TODO(Phase 2-3): wire the real async pipeline:
        #   ice_ingestion.ingest_video -> ice_transcript.transcribe ->
        #   ice_segmentation.segment_transcript -> ice_concept_graph ->
        #   ice_checkpoints.place_checkpoints -> ice_exercise_gen ->
        #   persist via ORM.
        # For now, just mark ready so the frontend can render the (empty) shell.
        curriculum.status = "ready"
        curriculum.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info(f"process_video: curriculum {curriculum_id} marked ready (stub)")
