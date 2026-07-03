"""FastAPI app factory + middleware wiring."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ice_shared import settings
from ice_shared.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    log = get_logger("ice_api")

    app = FastAPI(
        title="Interactive Curriculum Engine API",
        version="0.1.0",
        description="Convert tutorial videos into interactive, adaptive learning sessions.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # TenantMiddleware binds tenant_id from JWT -> context var -> RLS (risk E25).
    # Rate-limit per tenant (risk E18, E21).

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.env}

    # Routers are registered here as they land in each phase:
    #   from ice_api.routers import curriculum, sessions, eval, progress, admin
    #   app.include_router(curriculum.router, prefix="/ai", tags=["curriculum"])
    #   app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
    #   app.include_router(eval.router, prefix="/ai", tags=["evaluation"])
    #   app.include_router(progress.router, prefix="/progress", tags=["progress"])
    #   app.include_router(admin.router, prefix="/admin", tags=["instructor"])

    log.info("ice_api.create_app", env=settings.env, cors_origins=origins)
    return app


app = create_app()


def run() -> None:
    """Entry point for the `ice-api` console script."""
    import uvicorn

    uvicorn.run(
        "ice_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.env == "dev",
        log_level=settings.log_level.lower(),
    )
