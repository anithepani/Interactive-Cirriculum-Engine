from __future__ import annotations

import sys
import os

# Add the *src* folder of ice_shared to the path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'libs', 'shared', 'src'))

# Windows async event loop fix.
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
import uuid


async def seed() -> None:
    from ice_shared.db import get_engine
    from sqlalchemy import text

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    curriculum_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

    engine = get_engine()
    async with engine.begin() as conn:
        # Clear existing data to ensure a clean, repeatable seed.
        await conn.execute(text("TRUNCATE TABLE tenants CASCADE"))

        # SET LOCAL does not support parameters; use f-string with the UUID string.
        await conn.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))

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