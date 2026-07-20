"""add_skill_state_columns.py – one-time additive migration for M10/M11.

Adds two nullable columns to ``skill_model`` so the adaptive controller (M10)
and progress tracker (M11) can persist per-(user, concept) state without
touching the existing scalar ``mastery``/``attempts`` columns:

  - ``weak_concepts`` (JSON, nullable): list of concept slugs flagged weak.
  - ``difficulty``    (INTEGER, nullable, default 3): recommended next
    difficulty from the adaptive heuristic.

Both are additive + nullable, so existing reads/writes are unaffected
(zero-regression). Safe to run multiple times (IF NOT EXISTS).

Usage:  python add_skill_state_columns.py
Rollback:  ALTER TABLE skill_model DROP COLUMN weak_concepts, DROP COLUMN difficulty;
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


async def _add_column(conn, column_def: str, col_name: str) -> None:
    await conn.execute(
        text(f"ALTER TABLE skill_model ADD COLUMN IF NOT EXISTS {column_def}")
    )
    print(f"  > Ensured column: {col_name}")


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    engine = create_async_engine(DATABASE_URL, echo=False)

    columns = [
        ("weak_concepts JSON", "weak_concepts"),
        ("difficulty INTEGER DEFAULT 3", "difficulty"),
    ]

    async with engine.begin() as conn:
        for col_def, col_name in columns:
            await _add_column(conn, col_def, col_name)

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
