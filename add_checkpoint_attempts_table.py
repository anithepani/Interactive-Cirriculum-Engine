"""add_checkpoint_attempts_table.py – additive migration for donut/state persistence.

Creates the ``checkpoint_attempts`` table (Fix 2): one row per (user, checkpoint)
storing the final answer status ("correct" | "incorrect") and the learner's
submitted answer. This lets the progress donut and the locked review mode
survive a page reload, and enforces "no re-do after first attempt".

The table is created only if it does not already exist, so this is safe to run
multiple times and never touches existing data (zero-regression).

Usage:    python add_checkpoint_attempts_table.py
Rollback: DROP TABLE checkpoint_attempts;
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ice:ice_dev_password@localhost:5432/ice",
)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS checkpoint_attempts (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkpoint_id INTEGER NOT NULL REFERENCES checkpoints(id) ON DELETE CASCADE,
    status        VARCHAR NOT NULL,
    answer        TEXT,
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_checkpoint_attempts_user_cp UNIQUE (user_id, checkpoint_id)
)
"""

_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_checkpoint_attempts_user "
    "ON checkpoint_attempts (user_id)"
)


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_SQL))
        print("  > Ensured table: checkpoint_attempts")
        await conn.execute(text(_INDEX_SQL))
        print("  > Ensured index: ix_checkpoint_attempts_user")

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
