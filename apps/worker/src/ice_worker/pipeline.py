"""Pipeline entrypoint -- delegates to the real task in ice_worker.tasks.

Historical stub retained for import-compat; the actual pipeline DAG lives in
``ice_worker.tasks.generate_curriculum`` (autodiscovered by celery_app).
"""
from __future__ import annotations

from ice_worker.tasks.generate_curriculum import generate_curriculum

__all__ = ["generate_curriculum"]

