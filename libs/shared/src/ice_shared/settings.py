"""Typed application settings loaded from environment (see .env.example)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _Postgres(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    host: str = "localhost"
    port: int = 5432
    db: str = "ice"
    user: str = "ice"
    password: str = "ice_dev_password"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class _Redis(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    url: str = "redis://localhost:6379/0"


class _Celery(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CELERY_")
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"


class _S3(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="S3_")
    endpoint: str = "http://localhost:9000"
    access_key: str = "ice_minio"
    secret_key: str = "ice_minio_secret"
    region: str = "us-east-1"
    bucket: str = "ice-artifacts"
    use_path_style: bool = True


class _Judge0(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JUDGE0_")
    url: str = "http://localhost:2358"
    api_token: str = ""


class _Sandbox(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SANDBOX_")
    cpu_limit: int = 2
    memory_limit: int = 262144
    time_limit: int = 5
    network_disabled: bool = True


class _LLM(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")
    fallback_provider: str = "togetherai"
    fallback_model: str = "meta-llama/Llama-3.1-70B-Instruct"
    code_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    token_budget_per_curriculum: int = 250000


class _OpenAI(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_")
    api_key: str = ""
    model_primary: str = "gpt-4o"


class _ASR(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASR_")
    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "int8_float16"


class _OCR(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OCR_")
    engine: str = "paddleocr"
    gpu_enabled: bool = True


class _Pipeline(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PIPELINE_")
    max_video_duration_sec: int = 14400
    min_video_duration_sec: int = 30
    chunk_window_sec: int = 300
    checkpoint_min_gap_sec: int = 90
    checkpoint_avoid_final_sec: int = 30


class Settings(BaseSettings):
    """Root settings; import as `from ice_shared import settings`."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "dev"
    log_level: str = "INFO"
    app_name: str = "ice"
    cors_origins: str = "http://localhost:3000"

    database_url: str = ""
    db_rls_enabled: bool = True

    jwt_secret: str = "change_me_in_prod"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 60
    jwt_refresh_ttl_days: int = 7

    # Frontend URL (OAuth redirects, email links)
    frontend_url: str = "http://localhost:3000"

    # OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"

    # SMTP (email verification)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""

    sentry_dsn: str = ""
    prometheus_metrics_port: int = 9090

    # sub-sections
    postgres: _Postgres = Field(default_factory=_Postgres)
    redis: _Redis = Field(default_factory=_Redis)
    celery: _Celery = Field(default_factory=_Celery)
    s3: _S3 = Field(default_factory=_S3)
    judge0: _Judge0 = Field(default_factory=_Judge0)
    sandbox: _Sandbox = Field(default_factory=_Sandbox)
    llm: _LLM = Field(default_factory=_LLM)
    openai: _OpenAI = Field(default_factory=_OpenAI)
    asr: _ASR = Field(default_factory=_ASR)
    ocr: _OCR = Field(default_factory=_OCR)
    pipeline: _Pipeline = Field(default_factory=_Pipeline)

    @property
    def database_url_resolved(self) -> str:
        if self.database_url:
            return self.database_url
        if self.env == "dev":
            return "sqlite+aiosqlite:///./ice.db"
        return self.postgres.url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
