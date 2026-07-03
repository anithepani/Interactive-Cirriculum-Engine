"""Seed the dev database with one tenant, one user, and a sample curriculum.

Run: `make seed` (delegates to `uv run python scripts/seed-db.py`).
"""
from __future__ import annotations

import asyncio
import uuid


async def seed() -> None:
    from ice_shared.db import get_engine
    from sqlalchemy import text

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    curriculum_id = uuid.uuid4()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("SET LOCAL app.tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            text(
                "INSERT INTO tenants (id, name, slug) VALUES (:id, :name, :slug) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": str(tenant_id), "name": "Acme EdTech", "slug": "acme"},
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, name, role) "
                "VALUES (:id, :tid, :email, :name, 'learner') "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": str(user_id), "tid": str(tenant_id),
                "email": "learner@example.com", "name": "Dev Learner",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO curricula (id, tenant_id, video_ref, title, status, duration_sec) "
                "VALUES (:id, :tid, :ref, :title, 'ready', 600) ON CONFLICT DO NOTHING"
            ),
            {
                "id": str(curriculum_id), "tid": str(tenant_id),
                "ref": "https://www.youtube.com/watch?v=sample",
                "title": "Python Dictionaries (sample)",
            },
        )
    print(
        f"Seeded tenant={tenant_id} user={user_id} curriculum={curriculum_id}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
