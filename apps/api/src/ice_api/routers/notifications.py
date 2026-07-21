"""Notifications router — backs the bell dropdown.

GET  /api/v1/notifications        — list recent (last 50) + unread count
POST /api/v1/notifications/{id}/read — mark a notification read
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ice_shared.db import get_session
from ice_api.auth_utils import get_current_user
from ice_api.models import Notification, User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = (
        select(Notification)
        .where(Notification.user_id == int(current_user.id))
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    unread_stmt = (
        select(func.count(Notification.id))
        .where(
            Notification.user_id == int(current_user.id),
            Notification.read_at.is_(None),
        )
    )
    unread = (await session.execute(unread_stmt)).scalar_one()
    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "payload": n.payload,
                "curriculum_id": n.curriculum_id,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
        "unread_count": int(unread),
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == int(current_user.id),
        )
        .values(read_at=datetime.now(UTC).replace(tzinfo=None))
    )
    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="notification not found")
    await session.commit()
    return {"ok": True}
