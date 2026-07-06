from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class CelerySettings(BaseSettings):
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"

    model_config = {
        "env_prefix": "CELERY_",
    }


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ice.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ice-artifacts"

    # AI
    GROQ_API_KEY: str = Field(..., description="Required – set in .env or environment")

    # App settings – these must match what main.py expects
    log_level: str = "INFO"           # was LOG_LEVEL, now lowercase
    env: str = "dev"                  # already present
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Multi‑tenant
    TENANT_ID: str = "default-tenant"

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignore extra env vars not defined here

    @property
    def celery(self) -> CelerySettings:
        return CelerySettings(
            broker_url=self.REDIS_URL,
            result_backend=self.REDIS_URL,
        )


settings = Settings()