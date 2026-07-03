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
    DATABASE_URL: str = "postgresql+asyncpg://ice:ice@localhost:5432/ice"
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ice-artifacts"
    GROQ_API_KEY: str = Field(...)
    LOG_LEVEL: str = "INFO"
    TENANT_ID: str = "default-tenant"
    env: str = "dev"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    @property
    def celery(self) -> CelerySettings:
        return CelerySettings(
            broker_url=self.REDIS_URL,
            result_backend=self.REDIS_URL,
        )


settings = Settings()
