from __future__ import annotations

import contextvars
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .settings import settings

tenant_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_id", default=settings.TENANT_ID
)

engine = create_async_engine(settings.DATABASE_URL, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def set_tenant_context(tenant_id: str) -> None:
    tenant_id_context.set(tenant_id)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    tenant_id = tenant_id_context.get()
    async with async_session() as session:
        # Only set tenant context for PostgreSQL (RLS)
        if engine.dialect.name == "postgresql":
            await session.execute(
                text("SET LOCAL app.tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            )
        yield session
