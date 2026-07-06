from __future__ import annotations

import sys
import os

# Add repo root, libs, and src folder to sys.path
repo_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
libs_path = os.path.join(repo_root, "libs")
src_path = os.path.join(os.path.dirname(__file__), "..")

sys.path.insert(0, repo_root)
sys.path.insert(0, libs_path)
sys.path.insert(0, src_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ice_shared import settings
from ice_shared.logging import configure_logging, get_logger

# Import the router
from ice_api.routers import curricula

print("✅ curricula router imported successfully")

def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    log = get_logger("ice_api")

    app = FastAPI()

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

    # Register routers
    app.include_router(curricula.router)
    print("✅ curricula router registered")

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