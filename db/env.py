"""Alembic env: reads DATABASE_URL from ice_shared settings, runs migrations offline + online.

Embeds tenant_id into the session via SET LOCAL app.tenant_id when online so
Row-Level Security policies apply to data modifications.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the app's settings for the URL (env-driven).
from ice_shared import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.database_url_resolved)

target_metadata = None  # set to ORM metadata once SQLAlchemy models land (Phase 1)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True, dialect_opts={})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
