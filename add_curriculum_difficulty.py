"""add_curriculum_difficulty.py – additive migration for Phase 4 difficulty.

Adds the ``difficulty`` column to the ``curricula`` table: a learner-selected
difficulty ("easy" | "medium" | "hard") chosen on the upload page and threaded
through the pipeline (checkpoint spacing + exercise numeric difficulty).

The column is nullable with a ``'medium'`` default so existing curricula
(pre-migration) transparently behave as medium — zero-regression. Uses
``ADD COLUMN IF NOT EXISTS`` so the script is safe to run multiple times and
never touches existing data.

Usage:    python add_curriculum_difficulty.py
Rollback: ALTER TABLE curricula DROP COLUMN difficulty;
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

_ALTER_SQL = (
    "ALTER TABLE curricula "
    "ADD COLUMN IF NOT EXISTS difficulty VARCHAR DEFAULT 'medium'"
)

# Backfill any rows that predate the column (NULL) to the medium default so the
# whole table is consistent.
_BACKFILL_SQL = (
    "UPDATE curricula SET difficulty = 'medium' WHERE difficulty IS NULL"
)


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text(_ALTER_SQL))
        print("  > Ensured column: curricula.difficulty (default 'medium')")
        await conn.execute(text(_BACKFILL_SQL))
        print("  > Backfilled NULL difficulty -> 'medium'")

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
