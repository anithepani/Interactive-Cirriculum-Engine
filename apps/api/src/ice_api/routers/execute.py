from __future__ import annotations
import subprocess
import tempfile
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/execute", tags=["execution"])

class ExecuteRequest(BaseModel):
    code: str
    stdin: Optional[str] = ""
    language: str = "python"

class ExecuteResponse(BaseModel):
    status: str
    stdout: str
    stderr: str
    output: str
    passed: bool

@router.post("", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    try:
        # ---- Judge0 sandbox path (gated by SANDBOX_BACKEND=judge0) ----------
        # run_sandbox returns a signal result (backend="subprocess"/"unavailable")
        # when Judge0 is disabled or unreachable, in which case we fall through
        # to the original local-subprocess path below (zero-regression).
        try:
            from ice_shared import run_sandbox

            sb = run_sandbox(request.code, language=request.language, stdin=request.stdin or "")
            if sb.backend == "judge0":
                output = sb.stdout or sb.stderr or sb.error or "No output"
                return ExecuteResponse(
                    status="success",
                    stdout=sb.stdout,
                    stderr=sb.stderr or sb.error,
                    output=output,
                    passed=bool(sb.passed),
                )
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 - never let sandbox wiring break /execute
            pass

        # ---- Local subprocess fallback (default) ----------------------------
        # Only Python is supported in this fallback
        if request.language != "python":
            raise HTTPException(status_code=400, detail="Only Python is supported in this fallback")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(request.code)
            f.flush()
            filename = f.name

        try:
            result = subprocess.run(
                ['python', filename],
                input=request.stdin,
                capture_output=True,
                text=True,
                timeout=10
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            passed = result.returncode == 0
            output = stdout or stderr or "No output"
            return ExecuteResponse(
                status="success",
                stdout=stdout,
                stderr=stderr,
                output=output,
                passed=passed
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Execution timed out")
        finally:
            try:
                os.unlink(filename)
            except:
                pass

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))