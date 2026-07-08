from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ice_shared import configure_logging, get_logger, settings
from ice_api.routers import curricula


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    log = get_logger("ice_api")

    app = FastAPI(redirect_slashes=False)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.env}

    app.include_router(curricula.router)

    log.info(f"ice_api.create_app: env={settings.env}, cors_origins={origins}")
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
