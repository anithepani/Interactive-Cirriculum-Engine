from __future__ import annotations
import sys
import os
import logging
import asyncio
import traceback
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ice_shared.db import get_session, set_tenant_context
from ice_api.auth_utils import get_current_user
from ice_api.models import Curriculum, Tenant, Segment, Concept, Checkpoint, Exercise, User
from ice_api.process import process_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])


class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None


class EvaluateRequest(BaseModel):
    checkpoint_id: int
    answer: str


@router.get("/", response_model=List[Dict[str, Any]])
async def list_curricula(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant_id = current_user.tenant_id
    set_tenant_context(str(tenant_id))
    stmt = select(Curriculum).where(Curriculum.tenant_id == tenant_id).order_by(Curriculum.created_at.desc())
    result = await session.execute(stmt)
    curricula = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "ready_at": c.ready_at.isoformat() if c.ready_at else None,
        }
        for c in curricula
    ]


@router.post("/", response_model=Dict[str, Any])
async def create_curriculum(
    data: CurriculumCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        curriculum = Curriculum(
            tenant_id=tenant_id,
            title=data.title or "Untitled",
            source_ref=data.video_url,
        )
        session.add(curriculum)
        await session.commit()
        await session.refresh(curriculum)

        # Run processing in background (dispatches the Celery task).
        asyncio.create_task(process_video(curriculum.id, data.video_url, tenant_id))

        return {"curriculum_id": curriculum.id, "status": "queued"}

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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(str(current_user.tenant_id))
        stmt = select(Checkpoint).where(Checkpoint.id == payload.checkpoint_id)
        res = await session.execute(stmt)
        cp = res.scalar_one_or_none()
        if not cp:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        # Placeholder evaluation: accept any non-empty answer
        passed = bool(payload.answer and payload.answer.strip())
        return {"status": "ok", "passed": passed}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Evaluation error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{curriculum_id}", response_model=Dict[str, Any])
async def get_curriculum(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(str(current_user.tenant_id))

        # Fetch curriculum
        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        # Fetch related segments, concepts, checkpoints
        seg_stmt = select(Segment).where(Segment.curriculum_id == curriculum_id)
        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        conc_stmt = select(Concept).where(Concept.curriculum_id == curriculum_id)
        conc_result = await session.execute(conc_stmt)
        concepts = conc_result.scalars().all()

        cp_stmt = select(Checkpoint).where(Checkpoint.curriculum_id == curriculum_id)
        cp_result = await session.execute(cp_stmt)
        checkpoints = cp_result.scalars().all()

        # Fetch exercises for these checkpoints
        if checkpoints:
            cp_ids = [cp.id for cp in checkpoints]
            ex_stmt = select(Exercise).where(Exercise.checkpoint_id.in_(cp_ids))
            ex_result = await session.execute(ex_stmt)
            exercises = ex_result.scalars().all()
            exercise_map = {ex.checkpoint_id: ex for ex in exercises}
        else:
            exercise_map = {}

        return {
            "id": curriculum.id,
            "title": curriculum.title,
            "created_at": curriculum.created_at.isoformat() if curriculum.created_at else None,
            "status": curriculum.status,
            "ready_at": curriculum.ready_at.isoformat() if curriculum.ready_at else None,
            "video_url": curriculum.source_ref,
            "segments": [
                {
                    "id": seg.id,
                    "title": seg.title,
                    "summary": seg.summary,
                    "start": seg.start_time,
                    "end": seg.end_time,
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
            "checkpoints": [
                {
                    "id": cp.id,
                    "ts": cp.ts,
                    "segment_id": cp.segment_id,
                    "concept_id": cp.concept_id,
                    "exercise_type": cp.exercise_type,
                    "difficulty": cp.difficulty,
                    "exercise": exercise_map.get(cp.id).payload if exercise_map.get(cp.id) else None,
                }
                for cp in checkpoints
            ],
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))