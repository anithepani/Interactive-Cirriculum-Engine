"""Shared FastAPI dependencies: DB session, current user, tenant context."""
from __future__ import annotations

from typing import AsyncIterator

from ice_shared.db import get_session
from ice_api.auth_utils import get_current_user
from ice_api.models import User

__all__ = ["get_db", "current_user", "get_current_user"]


async def get_db() -> AsyncIterator:
    """Yield an async DB session with RLS tenant context set."""
    async for session in get_session():
        yield session


async def current_user() -> User:
    """Resolve the JWT bearer token to the authenticated User."""
    raise NotImplementedError("Use Depends(get_current_user) directly in route handlers")
