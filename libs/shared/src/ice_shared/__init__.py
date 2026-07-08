"""ice-shared: cross-cutting utilities (config, logging, tenant, clients)."""

from ice_shared.settings import settings
from ice_shared.logging import configure_logging, get_logger, bind_context
from ice_shared.tenant import TenantContext, current_tenant_id, set_tenant_context
from ice_shared.db import (
    Base,
    get_engine,
    get_session_factory,
    get_session,
    async_session,
)
from ice_shared.redis_client import get_redis
from ice_shared.s3 import get_s3_client, tenant_prefix

__all__ = [
    "settings",
    "configure_logging",
    "get_logger",
    "bind_context",
    "TenantContext",
    "current_tenant_id",
    "set_tenant_context",
    "Base",
    "get_engine",
    "get_session_factory",
    "get_session",
    "async_session",
    "get_redis",
    "get_s3_client",
    "tenant_prefix",
]

__version__ = "0.1.0"
