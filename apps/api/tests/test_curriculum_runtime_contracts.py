from ice_api.models import Session
from ice_api.routers.curricula import ProgressPing


def test_session_maps_tenant_and_single_user_curriculum_constraint():
    assert "tenant_id" in Session.__table__.columns
    constraints = {constraint.name for constraint in Session.__table__.constraints}
    assert "uq_sessions_user_curriculum" in constraints


def test_progress_ping_rejects_invalid_values():
    for payload in (
        {"position": -1},
        {"max_watched": -1},
        {"watched_delta": -1},
        {"watched_delta": 61},
        {"position": float("inf")},
    ):
        try:
            ProgressPing.model_validate(payload)
        except ValueError:
            continue
        raise AssertionError(f"accepted invalid progress payload: {payload}")
