"""MinIO/S3 client with tenant-scoped key helpers."""
from __future__ import annotations

from uuid import UUID

import boto3
from botocore.client import BaseClient

from ice_shared.settings import settings

_s3: BaseClient | None = None


def get_s3_client() -> BaseClient:
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3.endpoint,
            aws_access_key_id=settings.s3.access_key,
            aws_secret_access_key=settings.s3.secret_key,
            region_name=settings.s3.region,
            config=__import__("botocore").config.Config(
                s3={"addressing_style": "path" if settings.s3.use_path_style else "auto"}
            ),
        )
    return _s3


def tenant_prefix(tenant_id: UUID) -> str:
    """All tenant artifacts live under tenants/<tenant_id>/ in the bucket."""
    return f"tenants/{tenant_id}/"
