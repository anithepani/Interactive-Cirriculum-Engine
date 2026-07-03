from __future__ import annotations

from ice_worker.celery_app import celery_app


def test_celery_app_configured():
    assert celery_app.main == "ice"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.task_acks_late is True
