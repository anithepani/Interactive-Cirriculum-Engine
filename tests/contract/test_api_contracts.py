"""Consumer-driven contract tests.

Validate that the AI service endpoints (§5.3.2) emit shapes matching `libs/contracts/`.
Run in the `contract-check` CI job; a failure here means Aryan's producer and
Zubair's consumer have drifted.
"""
from __future__ import annotations

import pytest

from ice_contracts import CurriculumGenerateRequest, CurriculumGenerateResponse, EvaluateRequest


def test_curriculum_generate_request_round_trip():
    raw = {"video_ref": "https://youtube.com/watch?v=x", "tenant_id": "00000000-0000-0000-0000-000000000000"}
    req = CurriculumGenerateRequest.model_validate(raw)
    assert req.video_ref.startswith("https://")


def test_curriculum_generate_response_defaults_to_queued():
    resp = CurriculumGenerateResponse(curriculum_id="00000000-0000-0000-0000-000000000000")
    assert resp.status == "queued"


def test_evaluate_request_accepts_any_response_shape():
    req = EvaluateRequest(exercise_id="e1", response={"option_idx": 2})
    assert req.response["option_idx"] == 2


@pytest.mark.integration
def test_live_evaluate_endpoint_matches_contract():
    """TODO Phase 3: hit POST /ai/evaluate on a running api + assert the
    response validates as EvalResult."""
    pytest.skip("Phase 3 deliverable")
