"""add_source_frames_column.py – one-time additive migration for M4 segments.

Adds the ``source_frames`` column to the ``segments`` table so segment INSERTs
from the worker (persist_segments) succeed. The ORM model
(``apps/api/src/ice_api/models.py``) already declares this column; older
databases created before it was added are missing it, which causes:

    asyncpg.exceptions.UndefinedColumnError:
        column "source_frames" of relation "segments" does not exist

The column is JSONB with a ``'[]'`` default, so existing rows are backfilled
with an empty list and no data is lost. Additive + idempotent
(``ADD COLUMN IF NOT EXISTS``); safe to run multiple times.

Usage:  python add_source_frames_column.py
Rollback:  ALTER TABLE segments DROP COLUMN source_frames;
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
        text(f"ALTER TABLE segments ADD COLUMN IF NOT EXISTS {column_def}")
    )
    print(f"  > Ensured column: {col_name}")


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    engine = create_async_engine(DATABASE_URL, echo=False)

    columns = [
        ("source_frames JSONB DEFAULT '[]'", "source_frames"),
    ]

    async with engine.begin() as conn:
        for col_def, col_name in columns:
            await _add_column(conn, col_def, col_name)

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
