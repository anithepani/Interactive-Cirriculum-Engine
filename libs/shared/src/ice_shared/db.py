"""Async SQLAlchemy 2.0 engine + session factory with RLS support."""
from __future__ import annotations

import contextvars
from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ice_shared.settings import settings
from ice_shared.tenant import current_tenant_id, set_tenant_context

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

# Legacy string-based tenant context (used by curricula + auth routers)
tenant_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_id_str", default=None
)


def set_tenant_context(tenant_id: str) -> None:
    """Bind tenant id for the current async context (SQLite / legacy callers)."""
    tenant_id_context.set(tenant_id)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings.database_url_resolved
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=10 if not url.startswith("sqlite") else 5,
            max_overflow=20 if not url.startswith("sqlite") else 0,
            connect_args=connect_args,
        )
        # SQLite does NOT enforce foreign keys (and thus ON DELETE CASCADE)
        # unless PRAGMA foreign_keys=ON is set per-connection. Without this,
        # deleting a curriculum would orphan every child row on the dev DB.
        # Postgres enforces FKs natively, so this listener is a no-op there.
        if url.startswith("sqlite"):
            from sqlalchemy import event

            sync_engine = _engine.sync_engine

            @event.listens_for(sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
                cursor = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA foreign_keys=ON")
                finally:
                    cursor.close()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


def reset_engine() -> None:
    """Reset the engine + session factory singletons (sync, no await).

    Call at the start of each Celery task before ``asyncio.run`` so a fresh
    engine is created on the new event loop instead of reusing a stale one
    whose asyncpg connection pool is bound to a previous (now-closed) loop.
    """
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session with optional RLS tenant set."""
    factory = get_session_factory()
    async with factory() as session:
        engine = get_engine()
        if settings.db_rls_enabled and engine.name == "postgresql":
            tenant_id = current_tenant_id()
            if tenant_id is not None:
                await session.execute(
                    __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
            legacy_tenant = tenant_id_context.get()
            if legacy_tenant is not None:
                await session.execute(
                    __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
                    {"tid": legacy_tenant},
                )
        yield session


# Compat alias for callers that import `async_session` (e.g. legacy process.py).
async_session = get_session_factory()
