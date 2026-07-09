"""Celery application + broker/result backend configuration."""
from __future__ import annotations

from celery import Celery
from ice_shared import settings

celery_app = Celery(
    "ice",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                 # requeue on worker crash
    worker_prefetch_multiplier=1,       # fair scheduling for long tasks
    task_default_retry_delay=30,
    task_default_max_retries=3,
    task_time_limit=1800,               # 30 min hard cap per task
    task_soft_time_limit=1500,
    task_annotations={
        "ice_worker.tasks.transcribe.*": {"rate_limit": "1/m"},   # GPU bound
        "ice_worker.tasks.vision.*": {"rate_limit": "1/m"},
    },
)

# Auto-discover task modules:
celery_app.autodiscover_tasks([
    "ice_worker.tasks.generate_curriculum",
])


def run() -> None:
    """Entry point for the `ice-worker` console script."""
    from celery.__main__ import main

    main()
