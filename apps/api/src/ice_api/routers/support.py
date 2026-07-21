"""Support/feedback portal router.

POST /api/v1/support — ingests a support ticket and dispatches it to a Celery
task (``ice_worker.tasks.support_email.send_support_email``) so the SMTP
round-trip never blocks the request thread. Authenticated: the submitter is
captured from the JWT so support can follow up.
"""
from __future__ import annotations

import enum

from celery import Celery
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ice_shared import settings
from ice_api.auth_utils import get_current_user
from ice_api.models import User

router = APIRouter(prefix="/api/v1/support", tags=["support"])

# Send-only Celery instance (mirrors ice_api/process.py dispatch pattern).
_celery = Celery(
    "ice",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)


class SupportCategory(str, enum.Enum):
    bug = "bug"
    feature = "feature"
    general = "general"


class SupportRequest(BaseModel):
    category: SupportCategory
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)


@router.post("")
async def submit_support(
    body: SupportRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    _celery.send_task(
        "ice_worker.tasks.support_email.send_support_email",
        args=[
            current_user.email,
            int(current_user.id),
            body.category.value,
            body.subject,
            body.description,
        ],
    )
    return {"ok": True}
