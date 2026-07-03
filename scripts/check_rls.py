#!/usr/bin/env python3
"""Verify every tenant-scoped table has an RLS policy (CI safety check, risk E25).

Run in the `db-migration-check` CI job after `alembic upgrade head`.
Exits non-zero if any tenant-scoped table is missing its policy.
"""
from __future__ import annotations

import asyncio
import sys

EXPECTED = [
    "users", "curricula", "segments", "concepts", "concept_edges",
    "exercises", "tests", "sessions", "session_events", "eval_results",
    "skill_model", "artifacts", "audit_log",
]


async def main() -> int:
    from ice_shared.db import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_policies "
                    "WHERE policyname = 'tenant_isolation'"
                )
            )
        ).fetchall()
        protected = {r[0] for r in rows}

    missing = set(EXPECTED) - protected
    if missing:
        print(f"RLS policy missing on tables: {sorted(missing)}", file=sys.stderr)
        return 1
    print(f"OK: RLS policy present on all {len(EXPECTED)} tenant-scoped tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
