"""Verify Postgres Row-Level Security isolates tenants (risk E25).

Runs in the `db-migration-check` CI job. A P0 security regression if this fails.
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.mark.integration
async def test_tenant_a_cannot_see_tenant_b_rows():
    """Insert a row as tenant A; verify tenant B's session returns 0 rows."""
    # TODO Phase 1: spin two sessions with different app.tenant_id values,
    # insert a curriculum as A, query as B, assert empty.
    pytest.skip("Phase 1 deliverable - needs the ORM models wired")
