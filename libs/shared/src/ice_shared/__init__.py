"""ice-shared: cross-cutting utilities (config, logging, tenant, clients)."""

from ice_shared.settings import settings
from ice_shared.logging import get_logger, bind_context
from ice_shared.tenant import TenantContext, current_tenant_id
from ice_shared.db import get_engine, get_session_factory
from ice_shared.redis_client import get_redis
from ice_shared.s3 import get_s3_client, tenant_prefix

__all__ = [
    "settings",
    "get_logger",
    "bind_context",
    "TenantContext",
    "current_tenant_id",
    "get_engine",
    "get_session_factory",
    "get_redis",
    "get_s3_client",
    "tenant_prefix",
]

__version__ = "0.1.0"
