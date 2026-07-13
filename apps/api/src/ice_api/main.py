from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ice_shared import settings
from ice_shared.logging import configure_logging, get_logger

from ice_api.routers import auth, curricula, execute

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    log = get_logger("ice_api")

    app = FastAPI(
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
    app.include_router(auth.router)        # POST /api/v1/auth/signup, login, verify, etc.
    app.include_router(curricula.router)   # POST /api/v1/curricula, GET /api/v1/curricula, etc.
    app.include_router(execute.router)     # POST /api/v1/execute

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
