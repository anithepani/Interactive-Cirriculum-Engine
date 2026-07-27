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
    # backend: "subprocess" (host, default = zero-regression) | "judge0"
    backend: str = "subprocess"
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
    engine: str = "rapidocr"
    gpu_enabled: bool = False


class _Vision(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VISION_")
    # Sample every N seconds. 5s (was 2s) cuts candidate frames ~2.5x for a
    # typical screen recording with negligible signal loss — slide/code change
    # rarely move faster than this.
    extract_rate_sec: float = 5.0
    # Strict per-frame similarity threshold for near-duplicate suppression.
    # Lower = stricter (0.06 vs 0.08) so held/static slides collapse more.
    dedup_threshold: float = 0.06
    ocr_confidence_threshold: float = 0.7
    enable_heavy_fallbacks: bool = False
    # 0 = auto (min(cpu_count, 4)). ONNX releases the GIL during inference, so
    # threads give real parallelism without the daemonic-process crash that
    # ProcessPool hits inside Celery's preforked worker.
    max_workers: int = 0
    # Hard cap on OCR'd frames. 60 (was 150) bounds the worst-case OCR budget;
    # with 5s sampling + stricter dedup a 10-min video reaches ~1 / 3 ratio.
    max_frames: int = 60
    # Downscale frames wider than this (px) before OCR. 768 (was 1280) is still
    # legible for slide/code text and ~2x fewer pixels → faster inference.
    # 0 disables downscaling.
    ocr_max_width: int = 768
    # ONNX intra-op thread cap. With the threaded OCR pool each worker thread
    # shares one ONNX engine; capping intra-op threads to 1 avoids core
    # oversubscription (N threads x N cores). 0 = let ONNX Runtime decide.
    onnx_intra_op_threads: int = 1
    # Hard cap on frames that may invoke the heavy fallback path (upscale +
    # TrOCR). Prevents a single bad video from blowing the latency budget.
    # Only consulted when enable_heavy_fallbacks is True.
    max_fallback_frames: int = 3


class _Pipeline(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PIPELINE_")
    max_video_duration_sec: int = 14400
    min_video_duration_sec: int = 30
    chunk_window_sec: int = 300
    checkpoint_min_gap_sec: int = 90
    checkpoint_min_start_sec: int = 60  # no checkpoints before this (s)
    checkpoint_avoid_final_sec: int = 30
    run_tests: bool = False  # gate M8 test generation (CPU dev: off by default)
    # Caption harvesting (Block F): when True, the ingestor asks yt-dlp for the
    # video's existing subtitles (manual first, then auto-generated) and, if
    # found, uses them as the transcript — skipping Whisper ASR entirely for a
    # big latency/CPU win. Falls back to ASR when no captions exist.
    prefer_captions: bool = True
    caption_langs: str = "en,en-US,en-GB"  # priority order for subtitle language
    # ── Local file upload (Phase 2) ───────────────────────────────────────
    # Max accepted upload size (bytes) and allowed container extensions. Kept
    # here so the API validates before streaming to MinIO. 2 GiB default.
    upload_max_bytes: int = 2 * 1024 * 1024 * 1024
    upload_allowed_exts: str = ".mp4,.mov,.mkv,.webm,.avi,.m4v"


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
    # Support/feedback portal: destination inbox for submitted tickets. Falls
    # back to console-log if unset (mirrors email_service dev behaviour).
    support_email: str = ""
    # SSE stream auth: HMAC secret for signing short-lived query tokens
    # (EventSource cannot send Authorization headers). Falls back to jwt_secret.
    sse_token_secret: str = ""

    # LLM providers (Groq is the primary Phase-0 path; OpenAI/OpenRouter are fallback)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Rate-limit handling for the Groq client (429 backoff). Exponential:
    # sleep = groq_backoff_initial * 2**attempt + jitter (capped).
    groq_max_retries: int = 5
    groq_backoff_initial: float = 2.0

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
    vision: _Vision = Field(default_factory=_Vision)
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
