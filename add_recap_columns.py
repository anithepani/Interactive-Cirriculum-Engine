"""add_recap_columns.py – one-time migration for the Recap Video feature."""
from __future__ import annotations

import asyncio
import sys
import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://ice:ice_dev_password@localhost:5432/ice"
_IS_SQLITE = False

async def _add_column_pg(conn, column_def: str, col_name: str) -> None:
    await conn.execute(
        text(f"ALTER TABLE curricula ADD COLUMN IF NOT EXISTS {column_def}")
    )
    print(f"  > Ensured column: {col_name}")

async def main() -> None:
    print(f"Connecting to: {DATABASE_URL!r}")
    engine = create_async_engine(DATABASE_URL, echo=False)

    columns = [
        ("recap_status VARCHAR NOT NULL DEFAULT 'none'", "recap_status"),
        ("recap_url    VARCHAR", "recap_url"),
    ]

    async with engine.begin() as conn:
        for col_def, col_name in columns:
            await _add_column_pg(conn, col_def, col_name)

    await engine.dispose()
    print("\nMigration complete. >")

if __name__ == "__main__":
    asyncio.run(main())
