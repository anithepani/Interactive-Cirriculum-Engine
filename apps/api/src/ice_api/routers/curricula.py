from __future__ import annotations
import sys
import os
import logging
import asyncio
import traceback
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ice_shared.db import get_session, set_tenant_context
from ice_api.auth_utils import get_current_user
from ice_api.models import Curriculum, Tenant, Segment, Concept, Checkpoint, Exercise, User
from ice_api.process import process_video, trigger_recap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])


class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None


class EvaluateRequest(BaseModel):
    checkpoint_id: int
    answer: str


def _exercise_payload(exercise: Optional[Exercise]) -> Optional[Dict[str, Any]]:
    """Return the exercise JSON the frontend renders, always including ``type``.

    New rows store ``{..., question, type}`` via persist_exercises; older rows
    only have the type-specific sub-dict. Merging ``type`` here lets the
    frontend route coding vs. mcq vs. conceptual correctly without needing a
    re-process of existing curricula.
    """
    if exercise is None:
        return None
    payload = dict(exercise.payload or {})
    payload.setdefault("type", exercise.type.value if exercise.type else None)
    return payload or None


@router.get("", response_model=List[Dict[str, Any]])
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
            "recap_status": c.recap_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "ready_at": c.ready_at.isoformat() if c.ready_at else None,
        }
        for c in curricula
    ]


@router.post("", response_model=Dict[str, Any])
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

        cp_stmt = select(Checkpoint).where(Checkpoint.id == payload.checkpoint_id)
        cp_res = await session.execute(cp_stmt)
        cp = cp_res.scalar_one_or_none()
        if not cp:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        # Load the exercise so we can validate the answer against its payload.
        ex_stmt = select(Exercise).where(Exercise.checkpoint_id == cp.id)
        ex_res = await session.execute(ex_stmt)
        exercise = ex_res.scalar_one_or_none()

        answer = (payload.answer or "").strip()
        if exercise is None:
            # No exercise generated yet; fall back to non-empty check.
            return {"status": "ok", "passed": bool(answer)}

        ex_type = exercise.type.value if exercise.type else ""
        data: Dict[str, Any] = exercise.payload or {}

        if ex_type == "mcq":
            options = data.get("options") or []
            answer_idx = data.get("answer_idx", data.get("answer_index"))
            try:
                correct = options[int(answer_idx)] if answer_idx is not None else None
            except (IndexError, TypeError, ValueError):
                correct = None
            passed = bool(answer) and answer == correct
        elif ex_type == "conceptual":
            reference = data.get("reference_answer") or ""
            min_sim = float(data.get("min_similarity", 0.7) or 0.7)
            ratio = SequenceMatcher(None, answer.lower(), reference.lower()).ratio()
            passed = bool(answer) and bool(reference) and ratio >= min_sim
        else:
            # coding / debug route through /api/v1/execute; here we only
            # accept a non-empty answer so progress can be recorded.
            passed = bool(answer)

        return {"status": "ok", "passed": passed}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Evaluation error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{curriculum_id}/recap")
async def generate_recap(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        if curriculum.recap_status == "processing":
            raise HTTPException(status_code=409, detail="Recap is already generating")
            
        curriculum.recap_status = "processing"
        await session.commit()

        # Dispatch background task
        asyncio.create_task(trigger_recap(curriculum.id, tenant_id))

        return {"status": "processing"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_recap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{curriculum_id}")
async def delete_curriculum(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        await session.delete(curriculum)
        await session.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error deleting curriculum: {e}", exc_info=True)
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
            "recap_status": curriculum.recap_status,
            "recap_url": curriculum.recap_url,
            "recap_transcript_html": curriculum.recap_transcript_html,
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
                    "exercise": _exercise_payload(exercise_map.get(cp.id)),
                }
                for cp in checkpoints
            ],
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
