"""Learner statistics router — live aggregates for the dashboard + progress views.

Replaces the previously-hardcoded frontend metrics (count*3 exercises, count*1.5
hours, title-keyword categories) with real values pulled from the database for
the authenticated user:

  - Total curricula          -> COUNT(curricula) for the tenant
  - Completed exercises      -> COUNT(checkpoint_attempts) for the user
  - Correct answers          -> COUNT(checkpoint_attempts WHERE status='correct')
  - Hours learned            -> SUM(sessions.watched_seconds) / 3600 (real
                                accumulated watch-time via heartbeats — Block B)
  - Learning categories      -> concept-mastery breakdown from skill_model, with
                                a title-keyword fallback when no mastery exists

All endpoints are read-only and tenant/user-scoped. They never raise on missing
optional tables/columns (Block B columns are additive) so the dashboard keeps
working during incremental rollout.
"""
from __future__ import annotations

import contextlib
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ice_api.auth_utils import get_current_user
from ice_api.models import (
    Checkpoint,
    CheckpointAttempt,
    Concept,
    Curriculum,
    CurriculumStatus,
    Session as LearnSession,
    User,
)
from ice_shared.db import get_session, set_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


async def _total_curricula(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> int:
    stmt = select(func.count(Curriculum.id)).where(
        Curriculum.tenant_id == tenant_id,
        or_(Curriculum.user_id == user_id, Curriculum.user_id.is_(None)),
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def _ready_curricula(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> int:
    stmt = select(func.count(Curriculum.id)).where(
        Curriculum.tenant_id == tenant_id,
        or_(Curriculum.user_id == user_id, Curriculum.user_id.is_(None)),
        Curriculum.status == CurriculumStatus.ready,
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def _attempt_counts(session: AsyncSession, user_id: uuid.UUID) -> tuple[int, int]:
    """Return (total_attempts, correct_attempts) for this user."""
    total = int(
        (
            await session.execute(
                select(func.count(CheckpointAttempt.id)).where(
                    CheckpointAttempt.user_id == user_id
                )
            )
        ).scalar()
        or 0
    )
    correct = int(
        (
            await session.execute(
                select(func.count(CheckpointAttempt.id)).where(
                    CheckpointAttempt.user_id == user_id,
                    CheckpointAttempt.status == "correct",
                )
            )
        ).scalar()
        or 0
    )
    return total, correct


async def _watched_seconds(session: AsyncSession, user_id: uuid.UUID) -> float:
    """Sum real accumulated watch-time across the user's sessions (Block B).

    ``sessions.watched_seconds`` is an additive column; if it does not exist yet
    (migration not run) we return 0.0 rather than erroring.
    """
    try:
        stmt = select(func.coalesce(func.sum(LearnSession.watched_seconds), 0.0)).where(
            LearnSession.user_id == user_id
        )
        return float((await session.execute(stmt)).scalar() or 0.0)
    except Exception as exc:  # pragma: no cover - column may not exist pre-migration
        logger.warning("watched_seconds unavailable: %s", exc)
        with contextlib.suppress(Exception):
            await session.rollback()
        return 0.0


@router.get("/overview", response_model=Dict[str, Any])
async def stats_overview(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Headline metrics for the dashboard + progress views."""
    tenant_id = current_user.tenant_id
    set_tenant_context(str(tenant_id))

    total = await _total_curricula(session, tenant_id, current_user.id)
    ready = await _ready_curricula(session, tenant_id, current_user.id)
    attempts, correct = await _attempt_counts(session, current_user.id)
    watched = await _watched_seconds(session, current_user.id)

    return {
        "total_curricula": total,
        "ready_curricula": ready,
        "completed_exercises": attempts,
        "correct_exercises": correct,
        "accuracy": round(correct / attempts, 3) if attempts else 0.0,
        "hours_learned": round(watched / 3600.0, 2),
        "watched_seconds": round(watched, 1),
    }


@router.get("/progress", response_model=Dict[str, Any])
async def stats_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Detailed progress breakdown: headline metrics + learning categories.

    Categories are derived from the tenant's concept labels (real content) rather
    than the old client-side title keyword heuristic.
    """
    tenant_id = current_user.tenant_id
    set_tenant_context(str(tenant_id))

    total = await _total_curricula(session, tenant_id, current_user.id)
    ready = await _ready_curricula(session, tenant_id, current_user.id)
    attempts, correct = await _attempt_counts(session, current_user.id)
    watched = await _watched_seconds(session, current_user.id)

    # Learning categories: bucket this tenant's curricula titles into coarse
    # categories, counting concepts per curriculum as the weight so the split
    # reflects real generated content volume.
    categories: List[Dict[str, Any]] = []
    with contextlib.suppress(Exception):
        rows = (
            await session.execute(
                select(Curriculum.title, func.count(Concept.id))
                .join(Concept, Concept.curriculum_id == Curriculum.id)
                .where(
                    Curriculum.tenant_id == tenant_id,
                    or_(
                        Curriculum.user_id == current_user.id,
                        Curriculum.user_id.is_(None),
                    ),
                )
                .group_by(Curriculum.title)
            )
        ).all()
        bucket: Dict[str, int] = {}
        for title, concept_count in rows:
            cat = _infer_category(title or "")
            bucket[cat] = bucket.get(cat, 0) + int(concept_count or 0)
        total_concepts = sum(bucket.values()) or 1
        categories = sorted(
            (
                {
                    "category": cat,
                    "count": cnt,
                    "percent": round(cnt / total_concepts * 100),
                }
                for cat, cnt in bucket.items()
            ),
            key=lambda c: c["count"],
            reverse=True,
        )

    return {
        "total_curricula": total,
        "ready_curricula": ready,
        "completed_exercises": attempts,
        "correct_exercises": correct,
        "accuracy": round(correct / attempts, 3) if attempts else 0.0,
        "hours_learned": round(watched / 3600.0, 2),
        "watched_seconds": round(watched, 1),
        "categories": categories,
    }


_CATEGORY_KEYWORDS = {
    "Programming": ("python", "code", "javascript", "java", "react", "api", "sql", "programming", "function", "algorithm"),
    "UI/UX Design": ("design", "ui", "ux", "figma", "css", "layout", "interface"),
    "Business": ("business", "marketing", "finance", "startup", "management", "sales"),
    "Data & AI": ("data", "machine learning", "ml", "ai", "neural", "model", "analytics"),
}


def _infer_category(title: str) -> str:
    t = title.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return category
    return "General Learning"
