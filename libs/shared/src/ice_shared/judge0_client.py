"""Judge0 code-execution sandbox client (M14).

A thin, dependency-free (stdlib ``urllib``) client for a self-hosted Judge0
instance. It submits code, polls for the result, and normalizes Judge0's
status codes into a small :class:`SandboxResult` dataclass.

The module also exposes :func:`run_sandbox`, a backend-selecting facade used by
the API ``/execute`` endpoint and the M9 evaluator. Backend selection is driven
by ``SANDBOX_BACKEND`` (``judge0`` | ``subprocess``):

* ``subprocess`` (default) -> caller keeps its existing local execution path.
* ``judge0``               -> route through this client; if Judge0 is
  unreachable the caller may fall back to subprocess (zero-regression).

Nothing here runs unless a caller explicitly invokes it, so importing the
module is side-effect free.

Lead: Phase 4 (M14).
"""
from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ice_shared.settings import settings

logger = logging.getLogger(__name__)

# Judge0 language ids (1.13.x). Only Python is exercised by the app today; the
# map is here so additional languages can be wired without code changes.
_LANGUAGE_IDS: dict[str, int] = {
    "python": 71,       # Python 3.8.1
    "python3": 71,
    "javascript": 63,   # Node.js 12.14.0
    "typescript": 74,
    "c": 50,
    "cpp": 54,
    "c++": 54,
    "java": 62,
    "go": 60,
    "ruby": 72,
    "rust": 73,
    "bash": 46,
}

# Judge0 submission status ids. 3 == "Accepted" (ran to completion, exit 0).
_STATUS_ACCEPTED = 3
_STATUS_PROCESSING = (1, 2)  # In Queue, Processing


@dataclass
class SandboxResult:
    """Normalized result of a single sandbox execution."""

    passed: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    status: str = ""
    time: float | None = None
    memory: int | None = None
    error: str = ""
    backend: str = "judge0"
    raw: dict = field(default_factory=dict)


def language_id(language: str) -> int:
    """Resolve a human language name to a Judge0 language id (default Python)."""
    return _LANGUAGE_IDS.get((language or "python").strip().lower(), 71)


class Judge0Client:
    """Minimal Judge0 REST client (submit + poll)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        time_limit: float | None = None,
        memory_limit: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.judge0.url).rstrip("/")
        self.api_token = api_token if api_token is not None else settings.judge0.api_token
        self.time_limit = time_limit if time_limit is not None else float(settings.sandbox.time_limit)
        self.memory_limit = memory_limit if memory_limit is not None else int(settings.sandbox.memory_limit)

    # ---- low-level HTTP -------------------------------------------------- #
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            # Support both self-hosted auth headers Judge0 accepts.
            headers["X-Auth-Token"] = self.api_token
            headers["X-Auths-Token"] = self.api_token
        return headers

    def _request(self, method: str, path: str, body: dict | None = None, timeout: float = 10.0) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted internal host)
            payload = resp.read().decode("utf-8")
        return json.loads(payload) if payload else {}

    def is_available(self, timeout: float = 3.0) -> bool:
        """Health probe: returns True if Judge0 answers the languages endpoint."""
        try:
            self._request("GET", "/languages", timeout=timeout)
            return True
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Judge0 unavailable at %s: %s", self.base_url, exc)
            return False

    # ---- high-level execute --------------------------------------------- #
    def execute(
        self,
        code: str,
        language: str = "python",
        stdin: str = "",
        expected_output: str | None = None,
        poll_interval: float = 0.4,
        max_polls: int = 30,
    ) -> SandboxResult:
        """Submit ``code`` and poll until the run finishes (or times out)."""
        lang_id = language_id(language)
        submission = {
            "language_id": lang_id,
            "source_code": base64.b64encode((code or "").encode("utf-8")).decode("ascii"),
            "stdin": base64.b64encode((stdin or "").encode("utf-8")).decode("ascii"),
            "cpu_time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
        }
        if expected_output is not None:
            submission["expected_output"] = base64.b64encode(
                expected_output.encode("utf-8")
            ).decode("ascii")

        try:
            created = self._request(
                "POST",
                "/submissions?base64_encoded=true&wait=false",
                body=submission,
            )
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            return SandboxResult(passed=False, error=f"submit_failed: {exc}", status="error")

        token = created.get("token")
        if not token:
            return SandboxResult(passed=False, error="no_token", status="error", raw=created)

        result: dict = {}
        for _ in range(max_polls):
            try:
                result = self._request(
                    "GET",
                    f"/submissions/{token}?base64_encoded=true&fields=stdout,stderr,compile_output,message,status,time,memory,exit_code",
                    timeout=10.0,
                )
            except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
                return SandboxResult(passed=False, error=f"poll_failed: {exc}", status="error")
            status_id = (result.get("status") or {}).get("id")
            if status_id not in _STATUS_PROCESSING:
                break
            time.sleep(poll_interval)

        return self._parse(result)

    @staticmethod
    def _decode(value: str | None) -> str:
        if not value:
            return ""
        try:
            return base64.b64decode(value).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return str(value)

    def _parse(self, result: dict) -> SandboxResult:
        status = result.get("status") or {}
        status_id = status.get("id")
        status_desc = str(status.get("description", ""))
        stdout = self._decode(result.get("stdout"))
        stderr = self._decode(result.get("stderr"))
        compile_output = self._decode(result.get("compile_output"))
        message = self._decode(result.get("message"))
        # Surface compile errors / runtime messages through stderr for the UI.
        combined_err = "\n".join(p for p in (stderr, compile_output, message) if p).strip()
        exit_code = result.get("exit_code")
        try:
            exit_code = int(exit_code) if exit_code is not None else None
        except (TypeError, ValueError):
            exit_code = None
        time_val = result.get("time")
        try:
            time_val = float(time_val) if time_val is not None else None
        except (TypeError, ValueError):
            time_val = None

        return SandboxResult(
            passed=status_id == _STATUS_ACCEPTED,
            stdout=stdout,
            stderr=combined_err,
            exit_code=exit_code,
            status=status_desc,
            time=time_val,
            memory=result.get("memory"),
            raw=result,
        )


_client: Judge0Client | None = None


def get_judge0_client() -> Judge0Client:
    """Return a process-wide Judge0 client singleton."""
    global _client
    if _client is None:
        _client = Judge0Client()
    return _client


def run_sandbox(
    code: str,
    language: str = "python",
    stdin: str = "",
    expected_output: str | None = None,
) -> SandboxResult:
    """Backend-selecting facade used by the API + evaluator.

    Honors ``SANDBOX_BACKEND``. When set to ``judge0`` the code runs in the
    Judge0 sandbox; if Judge0 is unreachable the result carries
    ``backend="unavailable"`` so the caller can fall back to its local path.
    When set to anything else (default ``subprocess``) this returns a result
    with ``backend="subprocess"`` and the caller runs its existing logic.
    """
    backend = (settings.sandbox.backend or "subprocess").strip().lower()
    if backend != "judge0":
        return SandboxResult(passed=False, backend="subprocess", status="skipped")

    client = get_judge0_client()
    if not client.is_available():
        return SandboxResult(passed=False, backend="unavailable", status="unavailable")

    result = client.execute(code, language=language, stdin=stdin, expected_output=expected_output)
    result.backend = "judge0"
    return result
