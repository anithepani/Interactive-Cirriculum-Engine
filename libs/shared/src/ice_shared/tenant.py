"""Tenant context - the seam for Postgres RLS and S3 prefix scoping.

Every request/task binds the current tenant_id here; the DB session sets
`SET app.tenant_id = <id>` so RLS policies enforce isolation (risk E25).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator
from uuid import UUID

_current_tenant: ContextVar[UUID | None] = ContextVar("current_tenant", default=None)


def current_tenant_id() -> UUID | None:
    return _current_tenant.get()


def set_tenant_context(tenant_id: UUID | str) -> None:
    """Bind the current tenant (non-contextmanager convenience for request/task entry)."""
    _current_tenant.set(UUID(str(tenant_id)))


@contextmanager
def TenantContext(tenant_id: UUID) -> Iterator[UUID]:
    """Bind a tenant for the duration of a request or Celery task."""
    token = _current_tenant.set(tenant_id)
    try:
        yield tenant_id
    finally:
        _current_tenant.reset(token)
