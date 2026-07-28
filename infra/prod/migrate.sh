#!/usr/bin/env bash
# Run Alembic migrations against the production DB inside the API container.
#
# alembic is a dev-only dependency (pyproject.toml [dependency-groups] dev),
# so it is NOT in the runtime image (built with `uv sync --no-dev`).
# We install it ephemerally with `uv run --with alembic`.
#
# The canonical migration config is db/alembic.ini (shipped in the API image
# at /app/db/alembic.ini). db/env.py derives the sync SQLAlchemy URL from
# DATABASE_URL by replacing "+asyncpg" with "+psycopg" (psycopg3 is a runtime
# dependency of ice-shared). The container's env_file (.env) provides
# DATABASE_URL so the migration targets the correct Neon database.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"

echo ">> Running Alembic migrations (db/alembic.ini upgrade head) ..."
docker compose -f "${COMPOSE_FILE}" run --rm --no-deps api \
	sh -c 'uv run --with alembic alembic -c db/alembic.ini upgrade head'

echo ">> Migrations complete."
