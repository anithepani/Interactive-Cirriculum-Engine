"""add_curricula_user_id.py – additive migration for per-user curriculum ownership.

Adds a nullable ``user_id`` column to ``curricula`` (Block A follow-up) so that
duplicate-video validation and ownership can be scoped to an *individual user*
rather than the whole tenant. Two learners in the same tenant may each hold
their own curriculum instance for the same YouTube video; a single learner is
still blocked from creating a duplicate of a video they already own (ready).

Backfill: existing rows are assigned to the earliest (lowest id) user in the
same tenant, so historical data keeps a valid owner. Rows whose tenant has no
user are left NULL (harmless; the per-user check simply won't match them).

The column is additive + nullable, so existing reads/writes are unaffected
(zero-regression). Safe to run multiple times (guarded ADD COLUMN + idempotent
backfill of NULLs only).

Usage:    python add_curricula_user_id.py
Rollback: ALTER TABLE curricula DROP COLUMN user_id;
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


async def _existing_columns(conn, table: str, is_sqlite: bool) -> set[str]:
    if is_sqlite:
        rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).all()
        return {r[1] for r in rows}  # (cid, name, type, ...)
    rows = (
        await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table},
        )
    ).all()
    return {r[0] for r in rows}


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    is_sqlite = DATABASE_URL.startswith("sqlite")
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        existing = await _existing_columns(conn, "curricula", is_sqlite)

        if "user_id" not in existing:
            # SQLite cannot add a column with an inline FK via ALTER; add a plain
            # INTEGER there. Postgres gets a real FK with ON DELETE SET NULL so a
            # deleted user does not orphan-cascade their curricula away.
            if is_sqlite:
                await conn.execute(
                    text("ALTER TABLE curricula ADD COLUMN user_id INTEGER")
                )
            else:
                await conn.execute(
                    text(
                        "ALTER TABLE curricula ADD COLUMN IF NOT EXISTS user_id "
                        "INTEGER REFERENCES users(id) ON DELETE SET NULL"
                    )
                )
            print("  > Ensured column: curricula.user_id")
        else:
            print("  = column already present: curricula.user_id")

        # Index for the per-user duplicate lookup (idempotent).
        if is_sqlite:
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_curricula_user "
                    "ON curricula (user_id)"
                )
            )
        else:
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_curricula_user "
                    "ON curricula (user_id)"
                )
            )
        print("  > Ensured index: ix_curricula_user")

        # Backfill NULLs only: assign each curriculum to the earliest user in
        # its tenant. Runs on both engines with the same correlated subquery.
        result = await conn.execute(
            text(
                "UPDATE curricula SET user_id = ("
                "  SELECT MIN(u.id) FROM users u "
                "  WHERE u.tenant_id = curricula.tenant_id"
                ") WHERE user_id IS NULL"
            )
        )
        # rowcount is best-effort across drivers.
        try:
            print(f"  > Backfilled user_id on {result.rowcount} row(s)")
        except Exception:
            print("  > Backfilled user_id (rowcount unavailable)")

    await engine.dispose()
    print("\nMigration complete. >")


if __name__ == "__main__":
    asyncio.run(main())
