from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ice_shared import get_session, set_tenant_context
from ice_api.models import Concept, Curriculum, Exercise, Segment
from ice_api.process import process_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])


class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None


class EvaluateRequest(BaseModel):
    checkpoint_id: str
    answer: str


@router.get("", response_model=List[Dict[str, Any]])
async def list_curricula(
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    session: AsyncSession = Depends(get_session),
):
    set_tenant_context(tenant_id)
    stmt = (
        select(Curriculum)
        .where(Curriculum.tenant_id == UUID(tenant_id))
        .order_by(Curriculum.created_at.desc())
    )
    result = await session.execute(stmt)
    curricula = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        }
        for c in curricula
    ]


@router.post("", response_model=Dict[str, Any], status_code=202)
async def create_curriculum(
    data: CurriculumCreate,
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(tenant_id)

        curriculum = Curriculum(
            tenant_id=UUID(tenant_id),
            title=data.title or "Untitled",
            video_ref=data.video_url,
            duration_sec=0.0,
        )
        session.add(curriculum)
        await session.commit()
        await session.refresh(curriculum)

        # Run processing in background (stub: just flips status to 'ready').
        asyncio.create_task(process_video(str(curriculum.id), tenant_id))

        return {"curriculum_id": str(curriculum.id), "status": "queued"}

    except Exception as e:
        logger.error(f"Error in create_curriculum: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/evaluate")
async def evaluate(
    payload: EvaluateRequest,
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(tenant_id)

        # The checkpoint/exercise id arrives as a string. Lookup against the
        # exercises table (checkpoint data is folded into exercises per the
        # canonical migration).
        stmt = select(Exercise).where(Exercise.id == payload.checkpoint_id)
        res = await session.execute(stmt)
        exercise = res.scalar_one_or_none()
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise/checkpoint not found")

        # Placeholder evaluation: accept any non-empty answer.
        # Real evaluation engine (ice_evaluation) lands in Phase 3.
        passed = bool(payload.answer and payload.answer.strip())
        return {"status": "ok", "passed": passed}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Evaluation error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{curriculum_id}", response_model=Dict[str, Any])
async def get_curriculum(
    curriculum_id: str,
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(tenant_id)

        # Fetch curriculum
        stmt = select(Curriculum).where(Curriculum.id == UUID(curriculum_id))
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        # Fetch related segments, concepts, exercises (which carry checkpoint data).
        seg_stmt = select(Segment).where(Segment.curriculum_id == curriculum.id)
        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        conc_stmt = select(Concept).where(Concept.curriculum_id == curriculum.id)
        conc_result = await session.execute(conc_stmt)
        concepts = conc_result.scalars().all()

        ex_stmt = select(Exercise).where(Exercise.curriculum_id == curriculum.id)
        ex_result = await session.execute(ex_stmt)
        exercises = ex_result.scalars().all()

        return {
            "id": str(curriculum.id),
            "title": curriculum.title,
            "created_at": curriculum.created_at.isoformat() if curriculum.created_at else None,
            "status": curriculum.status,
            "completed_at": curriculum.completed_at.isoformat() if curriculum.completed_at else None,
            "video_url": curriculum.video_ref,
            "segments": [
                {
                    "id": seg.id,
                    "title": seg.title,
                    "summary": seg.summary,
                    "start": seg.start,
                    "end": seg.end,
                }
                for seg in segments
            ],
            "concepts": [
                {
                    "id": conc.id,
                    "label": conc.label,
                    "description": conc.description,
                    "difficulty": conc.difficulty,
                }
                for conc in concepts
            ],
            # Exercises carry checkpoint placement (ts, segment_id, concept_id, type, difficulty).
            # Exposed as "checkpoints" for frontend compatibility.
            "checkpoints": [
                {
                    "id": ex.id,
                    "ts": ex.ts,
                    "segment_id": ex.segment_id,
                    "concept_id": ex.concept_id,
                    "exercise_type": ex.type,
                    "difficulty": ex.difficulty,
                    "exercise": ex.payload,
                }
                for ex in exercises
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
