from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from ice_shared import run_sandbox
from pydantic import BaseModel

from ice_api.auth_utils import get_current_user
from ice_api.models import User

router = APIRouter(prefix="/api/v1/execute", tags=["execution"])


class ExecuteRequest(BaseModel):
    code: str
    stdin: str = ""
    language: str = "python"


class ExecuteResponse(BaseModel):
    status: str
    stdout: str
    stderr: str
    output: str
    passed: bool


@router.post("", response_model=ExecuteResponse)
async def execute_code(
    request: ExecuteRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Execute code only through the configured isolated Judge0 service."""
    try:
        sandbox = run_sandbox(
            request.code,
            language=request.language,
            stdin=request.stdin or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The code sandbox is unavailable",
        ) from exc

    if sandbox.backend != "judge0":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Isolated code execution is not configured",
        )

    output = sandbox.stdout or sandbox.stderr or sandbox.error or "No output"
    return ExecuteResponse(
        status="success",
        stdout=sandbox.stdout,
        stderr=sandbox.stderr or sandbox.error,
        output=output,
        passed=bool(sandbox.passed),
    )
