from __future__ import annotations
import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# Add the src folder to sys.path so ice_api is importable
src_path = os.path.join(os.path.dirname(__file__), "..")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Use direct imports from ice_api
from ice_shared.db import get_session, set_tenant_context
from ice_api.models import Curriculum, Tenant

router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])

class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None

@router.post("/", response_model=Dict[str, Any])
async def create_curriculum(
    data: CurriculumCreate,
    tenant_id: str = "default-tenant",
    session: AsyncSession = Depends(get_session),
):
    set_tenant_context(tenant_id)

    curriculum = Curriculum(
        tenant_id=tenant_id,
        source_type="youtube",
        source_ref=data.video_url,
        title=data.title or "Untitled",
        status="queued",
    )
    session.add(curriculum)
    await session.commit()
    await session.refresh(curriculum)

    return {"curriculum_id": curriculum.id, "status": "queued"}

@router.get("/ping")
async def ping():
    return {"ping": "pong"}

@router.get("/{curriculum_id}", response_model=Dict[str, Any])
async def get_curriculum(
    curriculum_id: int,
    tenant_id: str = "default-tenant",
    session: AsyncSession = Depends(get_session),
):
    set_tenant_context(tenant_id)

    stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
    result = await session.execute(stmt)
    curriculum = result.scalar_one_or_none()
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    return {
        "id": curriculum.id,
        "title": curriculum.title,
        "status": curriculum.status,
        "created_at": curriculum.created_at.isoformat() if curriculum.created_at else None,
        "ready_at": curriculum.ready_at.isoformat() if curriculum.ready_at else None,
        "segments": [],
        "concepts": [],
        "checkpoints": [],
    }
