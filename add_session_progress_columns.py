"""add_session_progress_columns.py – additive migration for video progress (Block B).

Adds two nullable columns to ``sessions`` so the player can persist granular
watch state (Feature 7):

  - ``max_watched_ts``  (FLOAT, default 0): the furthest second the learner has
    validly reached. Drives anti-scrub (no forward seek past this) + resume.
  - ``watched_seconds`` (FLOAT, default 0): real accumulated watch-time summed
    from heartbeat deltas — powers "Hours Learned" instead of raw video length.

Both are additive + defaulted, so existing reads/writes are unaffected
(zero-regression). Safe to run multiple times (IF NOT EXISTS on Postgres; a
guarded ALTER on SQLite which lacks IF NOT EXISTS for ADD COLUMN).

Usage:    python add_session_progress_columns.py
Rollback: ALTER TABLE sessions DROP COLUMN watched_seconds, DROP COLUMN max_watched_ts;
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

_COLUMNS = [
    ("max_watched_ts", "FLOAT DEFAULT 0"),
    ("watched_seconds", "FLOAT DEFAULT 0"),
]


async def _existing_columns(conn, is_sqlite: bool) -> set[str]:
    if is_sqlite:
        rows = (await conn.execute(text("PRAGMA table_info(sessions)"))).all()
        return {r[1] for r in rows}  # (cid, name, type, ...)
    rows = (
        await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'sessions'"
            )
        )
    ).all()
    return {r[0] for r in rows}


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    is_sqlite = DATABASE_URL.startswith("sqlite")
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        existing = await _existing_columns(conn, is_sqlite)
        for name, ddl in _COLUMNS:
            if name in existing:
                print(f"  = column already present: {name}")
                continue
            if is_sqlite:
                await conn.execute(
                    text(f"ALTER TABLE sessions ADD COLUMN {name} {ddl}")
                )
            else:
                await conn.execute(
                    text(f"ALTER TABLE sessions ADD COLUMN IF NOT EXISTS {name} {ddl}")
                )
            print(f"  > Ensured column: {name}")

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
