from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from ice_api.routers import execute


@pytest.mark.asyncio
async def test_execute_rejects_non_isolated_backend(monkeypatch):
    monkeypatch.setattr(
        execute,
        "run_sandbox",
        lambda *_args, **_kwargs: SimpleNamespace(backend="unavailable"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await execute.execute_code(
            execute.ExecuteRequest(code="print('unsafe')"),
            SimpleNamespace(),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Isolated code execution is not configured"


@pytest.mark.asyncio
async def test_execute_returns_judge0_result(monkeypatch):
    monkeypatch.setattr(
        execute,
        "run_sandbox",
        lambda *_args, **_kwargs: SimpleNamespace(
            backend="judge0",
            stdout="hello\n",
            stderr="",
            error="",
            passed=True,
        ),
    )

    response = await execute.execute_code(
        execute.ExecuteRequest(code="print('hello')"),
        SimpleNamespace(),
    )

    assert response.passed is True
    assert response.output == "hello\n"
