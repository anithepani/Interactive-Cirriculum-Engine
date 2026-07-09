#!/usr/bin/env python3
"""ORM-compatible dev seed: tenant + verified user + sample curriculum.

Works against whatever DATABASE_URL the app uses (SQLite ice.db or Postgres)
because it persists via the ice_api ORM models (Integer PKs). Creates a user
you can log in with to obtain a JWT for POST /api/v1/curricula.

Run:  uv run python scripts/seed_dev.py
Login: POST /api/v1/auth/login  {"email":"dev@ice.local","password":"devpass123"}
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure the workspace src roots are importable when run as a script.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "libs", "shared", "src"))
sys.path.insert(0, os.path.join(_ROOT, "libs", "contracts", "src"))
sys.path.insert(0, os.path.join(_ROOT, "apps", "api", "src"))

# Windows asyncio fix (matches db/seed/seed.py).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def seed() -> None:
    import ice_api.models  # noqa: F401  (registers tables on Base)
    from ice_api.auth_utils import hash_password
    from ice_api.models import Curriculum, Tenant, User
    from ice_shared.db import Base, get_engine, get_session_factory

    # Idempotently create tables if missing (no-op for existing ones).
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()
    async with factory() as session:
        # Wipe dev rows so the seed is repeatable.
        from sqlalchemy import delete

        await session.execute(delete(Curriculum))
        await session.execute(delete(User))
        await session.execute(delete(Tenant))
        await session.flush()

        tenant = Tenant(id=1, name="ICE Dev", slug="ice-dev", plan="free")
        user = User(
            id=1,
            tenant_id=1,
            email="dev@ice.local",
            name="Dev Learner",
            password_hash=hash_password("devpass123"),
            is_verified=True,
            is_active=True,
            role="learner",
        )
        session.add_all([tenant, user])
        await session.commit()

    print("Seeded tenant=1 user=1 (dev@ice.local / devpass123)")


if __name__ == "__main__":
    asyncio.run(seed())
