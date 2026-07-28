#!/usr/bin/env bash
# Run Alembic migrations against the production DB inside the API container.
#
# The production API image is built with `uv sync --no-dev`, which excludes
# alembic (a dev-only dependency in pyproject.toml [dependency-groups] dev) and
# also leaves the workspace libs (ice-shared etc.) uninstalled, so `pydantic`
# and other runtime transitive deps are missing at migration time.
#
# Fix: one-shot system install of the FULL workspace (root + all members) via
# `uv pip install --system -e /app` (resolves pydantic via ice-shared), plus an
# explicit `alembic` pin (dev-only), then run the migration.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"

echo ">> Installing full project deps (incl. alembic + pydantic) into API container ..."
docker compose -f "${COMPOSE_FILE}" run --rm --no-deps api \
	sh -c 'uv pip install --system -e /app alembic && \
	        alembic -c db/alembic.ini upgrade head'

echo ">> Migrations complete."
