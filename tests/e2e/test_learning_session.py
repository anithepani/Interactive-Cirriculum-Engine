"""End-to-end: submit video -> generate -> play -> checkpoint -> eval -> adapt."""
from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.skip(reason="Phase 4 deliverable - full user flow")
def test_full_learning_session():
    """UC-1 + UC-2 + UC-3 + UC-4 + UC-9 + UC-10 wired end-to-end."""
