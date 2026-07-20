"""ice-shared: cross-cutting utilities (config, logging, tenant, clients)."""

from ice_shared.settings import settings
from ice_shared.logging import get_logger, bind_context
from ice_shared.tenant import TenantContext, current_tenant_id
from ice_shared.db import Base, get_engine, get_session, get_session_factory, set_tenant_context, async_session, reset_engine
from ice_shared.redis_client import get_redis
from ice_shared.s3 import get_s3_client, tenant_prefix
from ice_shared.judge0_client import (
    Judge0Client,
    SandboxResult,
    get_judge0_client,
    run_sandbox,
)

__all__ = [
    "settings",
    "get_logger",
    "bind_context",
    "TenantContext",
    "current_tenant_id",
    "Base",
    "get_engine",
    "get_session",
    "get_session_factory",
    "set_tenant_context",
    "async_session",
    "reset_engine",
    "get_redis",
    "get_s3_client",
    "tenant_prefix",
    "Judge0Client",
    "SandboxResult",
    "get_judge0_client",
    "run_sandbox",
]

__version__ = "0.1.0"
