"""Shared FastAPI dependencies: DB session, current user, tenant context."""
from __future__ import annotations

from typing import AsyncIterator

from ice_shared.db import get_session


async def get_db() -> AsyncIterator:
    """Yield an async DB session with RLS tenant context set."""
    async for session in get_session():
        yield session


async def current_user() -> dict:
    """Resolve the JWT bearer -> user + tenant. TODO Phase 1."""
    return {"user_id": "todo", "tenant_id": "todo"}
