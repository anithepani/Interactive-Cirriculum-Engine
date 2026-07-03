"""Async SQLAlchemy 2.0 engine + session factory with RLS support."""
from __future__ import annotations

from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ice_shared.settings import settings
from ice_shared.tenant import current_tenant_id

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url_resolved,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session with RLS tenant set."""
    factory = get_session_factory()
    async with factory() as session:
        if settings.db_rls_enabled:
            tenant_id = current_tenant_id()
            if tenant_id is not None:
                await session.execute(
                    __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
        yield session
