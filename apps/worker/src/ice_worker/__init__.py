"""ice-worker: Celery worker orchestrating the async generation pipeline."""
from ice_worker.celery_app import celery_app

__all__ = ["celery_app"]
__version__ = "0.1.0"
