from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ice_shared import settings
from ice_shared.db import get_engine
from ice_shared.logging import configure_logging, get_logger
from sqlalchemy import text

from ice_api.routers import (
    auth,
    curricula,
    events,
    execute,
    notifications,
    recommendations,
    stats,
    support,
    review,
    tutor,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))


# Columns the ORM expects on ``users`` (see ice_api/models.py: User) but which
# historical migrations + ``init_db.py``'s ``Base.metadata.create_all`` left
# absent on some dev databases (create_all never ALTERs an existing table).
# Each entry is (column_name, SQL type clause, SQL server_default clause).
# The dict is intentionally additive: idempotent ``ADD COLUMN IF NOT EXISTS``
# statements preserve all existing accounts and are no-ops on a correct DB.
_USERS_DRIFT_COLUMNS = {
    "avatar_url": ("VARCHAR(255)", None),
    "streak_count": ("INTEGER", "0"),
    "streak_color": ("VARCHAR(50)", "'emerald'"),
    "token_version": ("INTEGER", "1"),
}


async def _ensure_users_columns() -> None:
    """Self-heal the ``users`` schema at startup so dev environments whose DB
    was seeded via ``init_db.py`` (``Base.metadata.create_all``) before these
    columns existed do not crash every auth request with
    ``UndefinedColumnError`` (manifesting as a 500 + non-JSON body that the
    frontend cannot parse).

    Best-effort: logged, never fatal. On a correctly-migrated DB every
    statement is a no-op. The canonical fix is the Alembic migration
    ``30965f7e6314_add_avatar_and_streak_fields_to_user`` plus
    ``a1b2c3d4e5f6_add_token_version_to_user``; this guard just keeps dev
    working when alembic hasn't been run (the ice-api Docker image does not
    ship alembic).
    """
    log = get_logger("ice_api")
    try:
        engine = get_engine()
        if engine.name != "postgresql":
            return
        async with engine.begin() as conn:
            for col, (col_type, default) in _USERS_DRIFT_COLUMNS.items():
                default_clause = f" DEFAULT {default}" if default is not None else ""
                await conn.execute(
                    text(
                        f"ALTER TABLE users "
                        f"ADD COLUMN IF NOT EXISTS {col} {col_type}{default_clause}"
                    )
                )
        log.info("ice_api._ensure_users_columns: users schema verified/healed")
    except Exception as exc:  # noqa: BLE001 - startup must not crash on heal
        log.warning("ice_api._ensure_users_columns: schema heal skipped: %s", exc)


# Tables whose ``_id_seq`` PostgreSQL sequences can drift behind manually /
# out-of-band inserted rows (a common dev-DB footgun when seed scripts INSERT
# with explicit ids, or rows predate ``CREATE SEQUENCE``). A lagging sequence
# makes ``nextval`` return an id that already exists -> ``UniqueViolationError``
# on the very first signup -> 500 + non-JSON body. ``setval`` to MAX(id) fixes
# it idempotently and is a no-op when the sequence is already ahead.
_ID_SEQ_TABLES = ("tenants", "users")


async def _resync_id_sequences() -> None:
    """Rebase each table's ``<table>_id_seq`` to ``MAX(id)`` so the next
    ``nextval`` does not collide with an existing row.

    Mirrors ``ALTER SEQUENCE ... RESTART`` but driven by live data, so it is
    safe regardless of how the rows got there. Best-effort: logged, never
    fatal (a missing sequence/table is skipped silently).
    """
    log = get_logger("ice_api")
    try:
        engine = get_engine()
        if engine.name != "postgresql":
            return
        async with engine.begin() as conn:
            for table in _ID_SEQ_TABLES:
                # Guard against the table not existing yet on a fresh DB.
                exists = (
                    await conn.execute(
                        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
                        {"t": table},
                    )
                ).scalar()
                if not exists:
                    continue
                # setval to MAX(id); if the table is empty, COALESCE lands on 1
                # so the next INSERT gets id=1. ``is_called=true`` ensures the
                # following nextval advances past the just-set value.
                await conn.execute(
                    text(
                        f"SELECT setval('{table}_id_seq', "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                    )
                )
        log.info("ice_api._resync_id_sequences: id sequences rebased")
    except Exception as exc:  # noqa: BLE001 - startup must not crash on heal
        log.warning("ice_api._resync_id_sequences: sequence resync skipped: %s", exc)


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    log = get_logger("ice_api")

    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Heal drifted ``users`` columns + resync lagging id sequences before
        # serving the first request so signup/login do not 500 with an
        # unparseable body. Both are best-effort and no-ops on a correct DB.
        await _ensure_users_columns()
        await _resync_id_sequences()
        yield

    app = FastAPI(
        lifespan=_lifespan,
        redirect_slashes=False,
        title="Interactive Curriculum Engine API",
        version="0.1.0",
        description="Convert tutorial videos into interactive, adaptive learning sessions.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.env}

    # Register routers
    app.include_router(auth.router)  # POST /api/v1/auth/signup, login, verify, etc.
    app.include_router(curricula.router)  # POST /api/v1/curricula, GET /api/v1/curricula, etc.
    app.include_router(execute.router)  # POST /api/v1/execute
    app.include_router(stats.router)  # GET /api/v1/stats/overview, /progress
    app.include_router(support.router)  # POST /api/v1/support (feedback -> Celery email)
    app.include_router(notifications.router)  # GET /api/v1/notifications, POST /{id}/read
    app.include_router(events.router)  # GET /api/v1/events/stream (SSE), POST /token
    app.include_router(recommendations.router)
    app.include_router(review.router)
    app.include_router(tutor.router)

    log.info(f"ice_api.create_app: env={settings.env}, cors_origins={origins}")
    return app


# --- Define app at the top level (required for uvicorn) ---
app = create_app()


# Optional: entry point for running with `python -m ice_api`
def run() -> None:
    import uvicorn

    uvicorn.run(
        "ice_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.env == "dev",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
