from __future__ import annotations
import sys
import os
import ast
import subprocess
import tempfile
import contextlib
import logging
import asyncio
import re
import traceback
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel

from ice_shared.db import get_session, set_tenant_context
from ice_api.auth_utils import get_current_user
from ice_api.models import (
    Curriculum,
    CurriculumStatus,
    Tenant,
    Segment,
    Concept,
    Checkpoint,
    Exercise,
    User,
    SkillModel,
    Session,
)
from ice_api.process import process_video, trigger_recap, trigger_signal

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Coding/debug sandbox execution (M9/M14)
# --------------------------------------------------------------------------- #
# The learner's code is run against the exercise's stored hidden tests. Backend
# selection honours SANDBOX_BACKEND via ice_shared.run_sandbox; when Judge0 is
# disabled/unreachable we fall back to a local subprocess (identical to the
# /api/v1/execute fallback), so this never breaks the existing flow.

_SANDBOX_TIMEOUT = 10


def _run_code_against_test(solution: str, test: str, language: str = "python") -> tuple[bool, str, str]:
    """Run ``solution + test`` once; return (passed, stdout, stderr).

    Tries Judge0 first (only if SANDBOX_BACKEND=judge0 and reachable), else a
    local Python subprocess. Any failure yields (False, "", <error>) so the
    caller always gets a well-formed result.
    """
    program = (solution or "").rstrip() + "\n\n" + (test or "").strip() + "\n"

    # 1) Judge0 path (gated + auto-fallback inside run_sandbox).
    try:
        from ice_shared import run_sandbox

        res = run_sandbox(program, language=language, stdin="")
        if res.backend == "judge0":
            return bool(res.passed), res.stdout or "", res.stderr or ""
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("run_sandbox failed, using subprocess fallback: %s", exc)

    # 2) Local subprocess fallback (Python only).
    if (language or "python").lower() not in ("python", "python3"):
        return False, "", f"Unsupported language for local fallback: {language}"
    path = ""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(program)
            path = f.name
        proc = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=_SANDBOX_TIMEOUT,
        )
        return proc.returncode == 0, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except OSError as exc:
        return False, "", f"EXEC_ERROR: {exc}"
    finally:
        if path:
            with contextlib.suppress(OSError):
                os.unlink(path)


def _collect_tests(data: Dict[str, Any], ex_type: str) -> list[str]:
    """Pull the assertion/test strings out of an exercise payload."""
    tests: list[str] = []
    if ex_type == "debug":
        tests = list(data.get("tests") or [])
    else:  # coding
        tests = list(data.get("tests_hidden") or []) + list(data.get("tests_visible") or [])
    return [t for t in tests if t and str(t).strip()]


def _validate_tests_against_reference(
    tests: list[str], data: Dict[str, Any], language: str
) -> list[str]:
    """Drop tests that the exercise's own reference solution fails.

    M7 test cases are LLM-generated and (with M8 validation gated off) can be
    self-inconsistent — a hallucinated expected value or a wrong function
    name/signature makes an assertion fail even 100%-correct learner code.
    Running each test against the known-good ``reference_solution`` first and
    keeping only the tests it passes removes those false-negatives. This is
    purely execution-based: quote style, whitespace, and comments are
    irrelevant because we execute, not string-compare.

    When there is no reference solution, all tests are kept unchanged
    (backward-compatible).
    """
    reference = str(data.get("reference_solution") or "").strip()
    if not reference:
        return tests
    validated: list[str] = []
    for test in tests:
        ok, _out, _err = _run_code_against_test(reference, test, language)
        if ok:
            validated.append(test)
        else:
            logger.info("Dropping self-inconsistent test (reference fails it): %r", test)
    return validated


def _is_skeleton_code(answer: str) -> bool:
    """True when a submission is an unimplemented stub, not a real solution.

    Issue 3: skeleton bodies like ``def f(n): pass`` run cleanly (exit 0) and
    were being marked correct. We reject a submission when EVERY function/class
    body (and the module top level) is a no-op: only ``pass``, ``...``, a bare
    docstring, or ``raise NotImplementedError``. Anything with real statements
    (assignments, calls, returns with a value, loops, prints, ...) is NOT a
    skeleton and passes this gate. Unparseable code is treated as non-skeleton
    so the normal test path can surface the syntax error.
    """
    src = (answer or "").strip()
    if not src:
        return True
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False  # let the test runner report the real error

    def _body_is_noop(body: list[ast.stmt]) -> bool:
        real = []
        for node in body:
            # A bare string expression is a docstring — ignore it.
            if isinstance(node, ast.Expr) and isinstance(
                getattr(node, "value", None), ast.Constant
            ) and isinstance(node.value.value, str):
                continue
            if isinstance(node, ast.Pass):
                continue
            # `...` (Ellipsis) stub.
            if isinstance(node, ast.Expr) and isinstance(
                getattr(node, "value", None), ast.Constant
            ) and node.value.value is Ellipsis:
                continue
            # `raise NotImplementedError` stub.
            if isinstance(node, ast.Raise):
                exc = node.exc
                name = None
                if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                    name = exc.func.id
                elif isinstance(exc, ast.Name):
                    name = exc.id
                if name == "NotImplementedError":
                    continue
            real.append(node)
        return len(real) == 0

    funcs = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if funcs:
        # Skeleton iff every defined function is a no-op.
        return all(_body_is_noop(fn.body) for fn in funcs)
    # No functions defined: skeleton iff the whole module is a no-op.
    return _body_is_noop(tree.body)


def _differential_test(answer: str, reference: str, language: str) -> tuple[bool, str, str]:
    """Compare learner output to the reference solution's output (Issue 3).

    Used when an exercise has NO usable stored tests. We execute both the
    learner's code and the known-good ``reference_solution`` and compare their
    stdout. Passing requires identical output AND that the reference itself ran
    cleanly (otherwise we can't trust the comparison). Returns
    (passed, learner_stdout, stderr). Fail-closed: any error => not passed.
    """
    ref = (reference or "").strip()
    if not ref:
        return False, "", "NO_REFERENCE"
    ref_ok, ref_out, _ref_err = _run_code_against_test(ref, "", language)
    if not ref_ok:
        # Reference doesn't run standalone (needs a driver we don't have) — we
        # cannot differentially verify, so fail closed rather than pass blindly.
        return False, "", "REFERENCE_NOT_RUNNABLE"
    learner_ok, learner_out, learner_err = _run_code_against_test(answer, "", language)
    if not learner_ok:
        return False, learner_out, learner_err or "Runtime error."
    passed = learner_out.strip() == ref_out.strip()
    return passed, learner_out, "" if passed else "Output does not match the reference solution."


def _evaluate_code_submission(answer: str, data: Dict[str, Any], ex_type: str) -> Dict[str, Any]:
    """Execute learner code against hidden tests; return passed + stdout/stderr."""
    tests = _collect_tests(data, ex_type)
    language = str(data.get("language", "python") or "python")

    if not answer.strip():
        return {"status": "ok", "passed": False, "stdout": "", "stderr": "No code submitted."}

    # Issue 3: reject unimplemented stubs up front. `def f(n): pass` runs cleanly
    # (exit 0) and used to be marked correct — never accept a no-op body.
    if _is_skeleton_code(answer):
        return {
            "status": "ok",
            "passed": False,
            "stdout": "",
            "stderr": "Submission is an empty/skeleton function — implement the solution.",
        }

    # Fix 1: guard against self-inconsistent LLM-generated tests by keeping only
    # those the reference solution itself passes.
    if tests:
        tests = _validate_tests_against_reference(tests, data, language)

    if not tests:
        # No (valid) stored tests. Issue 3: do NOT fall back to "exit 0 == pass"
        # (that let skeletons through). Instead differentially test against the
        # reference solution's output; if there's no runnable reference, fail
        # closed so an unverifiable submission is never marked correct.
        reference = str(data.get("reference_solution") or data.get("solution") or "")
        passed, out, err = _differential_test(answer, reference, language)
        if err in ("NO_REFERENCE", "REFERENCE_NOT_RUNNABLE"):
            # Surface a clear, non-misleading message; fail-closed.
            return {
                "status": "ok",
                "passed": False,
                "stdout": out,
                "stderr": (
                    "Could not verify this submission (no runnable tests or "
                    "reference solution available)."
                ),
            }
        return {"status": "ok", "passed": passed, "stdout": out, "stderr": err}

    passed_count = 0
    first_err = ""
    last_out = ""
    for test in tests:
        ok, out, err = _run_code_against_test(answer, test, language)
        if out:
            last_out = out
        if ok:
            passed_count += 1
        elif not first_err:
            first_err = err
    all_passed = passed_count == len(tests)
    return {
        "status": "ok",
        "passed": all_passed,
        "stdout": last_out,
        "stderr": "" if all_passed else first_err,
        "tests_passed": passed_count,
        "tests_total": len(tests),
    }


# --------------------------------------------------------------------------- #
# Skill-model update (M10 adaptive + M11 progress) — best-effort side effect
# --------------------------------------------------------------------------- #
# Folds each attempt into the learner's per-concept SkillModel row (mastery via
# EWMA, attempt count, weak-concept flag) and adjusts the next checkpoint's
# difficulty using the M10 heuristic. Wrapped so a failure here NEVER breaks the
# /evaluate response (zero-regression).

_MASTERY_EWMA_ALPHA = 0.4
_WEAK_THRESHOLD = 0.5


async def _update_skill_model(
    session: AsyncSession,
    user_id: int,
    cp: Checkpoint,
    exercise: Optional[Exercise],
    passed: bool,
) -> None:
    """Upsert the learner's SkillModel row for this checkpoint's concept."""
    try:
        concept_id = getattr(cp, "concept_id", None)
        if concept_id is None:
            return

        from ice_api.models import SkillModel as SkillModelRow

        score = 1.0 if passed else 0.0

        row_stmt = select(SkillModelRow).where(
            SkillModelRow.user_id == user_id,
            SkillModelRow.concept_id == concept_id,
        )
        row = (await session.execute(row_stmt)).scalar_one_or_none()

        if row is None:
            new_mastery = _MASTERY_EWMA_ALPHA * score
            row = SkillModelRow(
                user_id=user_id,
                concept_id=concept_id,
                mastery=new_mastery,
                attempts=1,
            )
            # Additive nullable columns (may not exist on very old DBs).
            with contextlib.suppress(Exception):
                row.weak_concepts = [] if new_mastery >= _WEAK_THRESHOLD else [str(concept_id)]
                base = int(getattr(cp, "difficulty", 3) or 3)
                row.difficulty = max(1, base - 1) if not passed else base
            session.add(row)
        else:
            prior = float(row.mastery or 0.0)
            row.mastery = (1 - _MASTERY_EWMA_ALPHA) * prior + _MASTERY_EWMA_ALPHA * score
            row.attempts = int(row.attempts or 0) + 1
            with contextlib.suppress(Exception):
                weak = list(getattr(row, "weak_concepts", None) or [])
                cid = str(concept_id)
                if row.mastery < _WEAK_THRESHOLD and cid not in weak:
                    weak.append(cid)
                elif row.mastery >= _WEAK_THRESHOLD and cid in weak:
                    weak.remove(cid)
                row.weak_concepts = weak
                # M10: lower next difficulty by 1 on fail, raise by 1 on pass.
                cur = int(getattr(row, "difficulty", None) or getattr(cp, "difficulty", 3) or 3)
                row.difficulty = max(1, cur - 1) if not passed else min(5, cur + 1)

        await session.commit()
    except Exception as exc:  # pragma: no cover - never break eval response
        logger.warning("skill_model update skipped: %s", exc)
        with contextlib.suppress(Exception):
            await session.rollback()


async def _get_checkpoint_attempt(
    session: AsyncSession, user_id: int, checkpoint_id: int
):
    """Return the learner's persisted CheckpointAttempt row, or None."""
    from ice_api.models import CheckpointAttempt

    stmt = select(CheckpointAttempt).where(
        CheckpointAttempt.user_id == user_id,
        CheckpointAttempt.checkpoint_id == checkpoint_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _record_checkpoint_attempt(
    session: AsyncSession,
    user_id: int,
    checkpoint_id: int,
    passed: bool,
    answer: str,
) -> None:
    """Persist the first attempt's status + answer so the checkpoint locks
    across reloads (Answer 2). Idempotent: a second call is ignored so the
    original attempt is never overwritten (answers are locked after the
    first submission)."""
    from ice_api.models import CheckpointAttempt

    try:
        existing = await _get_checkpoint_attempt(session, user_id, checkpoint_id)
        if existing is not None:
            return  # locked: keep the first attempt
        row = CheckpointAttempt(
            user_id=user_id,
            checkpoint_id=checkpoint_id,
            status="correct" if passed else "incorrect",
            answer=answer,
        )
        session.add(row)
        await session.commit()
    except Exception as exc:  # pragma: no cover - never break eval response
        logger.warning("checkpoint_attempt record skipped: %s", exc)
        with contextlib.suppress(Exception):
            await session.rollback()


router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])


class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None


class EvaluateRequest(BaseModel):
    checkpoint_id: int
    answer: str


class ProgressPing(BaseModel):
    # Current playhead position (seconds).
    position: float = 0.0
    # Highest contiguous timestamp the learner has legitimately watched.
    max_watched: float = 0.0
    # Watch-time accrued since the last ping (seconds of actual playback).
    watched_delta: float = 0.0


def _exercise_payload(exercise: Optional[Exercise]) -> Optional[Dict[str, Any]]:
    """Return the exercise JSON the frontend renders, always including ``type``.

    New rows store ``{..., question, type}`` via persist_exercises; older rows
    only have the type-specific sub-dict. Merging ``type`` here lets the
    frontend route coding vs. mcq vs. conceptual correctly without needing a
    re-process of existing curricula.
    """
    if exercise is None:
        return None
    payload = dict(exercise.payload or {})
    payload.setdefault("type", exercise.type.value if exercise.type else None)
    return payload or None


_YT_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/))([A-Za-z0-9_-]{11})"
)


def _extract_youtube_id(url: str) -> Optional[str]:
    """Return the 11-char YouTube video id from a URL, or None if not a YT URL."""
    if not url:
        return None
    match = _YT_ID_RE.search(url)
    return match.group(1) if match else None


async def _find_existing_ready_curriculum(
    session: AsyncSession, tenant_id: int, user_id: int, video_id: str
) -> Optional[Curriculum]:
    """Return this *user's* READY curriculum for the same YouTube video, if any.

    Scoped per individual learner (``user_id``) within their tenant: two users
    in the same tenant may each own their own instance of the same video, but a
    single learner is blocked from creating a duplicate of one they already own.
    Matches on the video id appearing in ``source_ref`` (handles the various
    YouTube URL shapes) and only treats ``ready`` rows as duplicates so failed
    generations can be retried.
    """
    stmt = select(Curriculum).where(
        Curriculum.tenant_id == tenant_id,
        Curriculum.user_id == user_id,
        Curriculum.status == CurriculumStatus.ready,
        Curriculum.source_ref.contains(video_id),
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def _cascade_delete_curriculum(session: AsyncSession, curriculum_id: int) -> None:
    """Purge all rows that hang off a curriculum, child-first.

    Covers grandchildren keyed off checkpoints/concepts/exercises/sessions that
    a naive ``DELETE curricula`` would orphan (or fail on, under FK enforcement):
    checkpoint_attempts, eval_results, skill_model, tests, session_events, then
    exercises, checkpoints, concept_edges, concepts, segments, sessions,
    artifacts. Uses bulk DELETE statements so it is efficient and backend-neutral.
    """
    from sqlalchemy import delete as sa_delete
    from ice_api.models import (
        CheckpointAttempt,
        ConceptEdge,
        EvalResult,
        SessionEvent,
        Test,
        Artifact,
    )

    # Resolve the id sets we need for grandchild deletes.
    cp_ids = (
        await session.execute(
            select(Checkpoint.id).where(Checkpoint.curriculum_id == curriculum_id)
        )
    ).scalars().all()
    concept_ids = (
        await session.execute(
            select(Concept.id).where(Concept.curriculum_id == curriculum_id)
        )
    ).scalars().all()
    exercise_ids = (
        (
            await session.execute(
                select(Exercise.id).where(Exercise.checkpoint_id.in_(cp_ids))
            )
        ).scalars().all()
        if cp_ids
        else []
    )
    session_ids = (
        await session.execute(
            select(Session.id).where(Session.curriculum_id == curriculum_id)
        )
    ).scalars().all()

    # 1) Grandchildren of exercises / checkpoints.
    if exercise_ids:
        await session.execute(
            sa_delete(EvalResult).where(EvalResult.exercise_id.in_(exercise_ids))
        )
        await session.execute(
            sa_delete(Test).where(Test.exercise_id.in_(exercise_ids))
        )
    if cp_ids:
        await session.execute(
            sa_delete(CheckpointAttempt).where(
                CheckpointAttempt.checkpoint_id.in_(cp_ids)
            )
        )
        await session.execute(
            sa_delete(Exercise).where(Exercise.checkpoint_id.in_(cp_ids))
        )
    # 2) Session events + sessions (watch-time / heartbeats).
    if session_ids:
        await session.execute(
            sa_delete(SessionEvent).where(SessionEvent.session_id.in_(session_ids))
        )
    await session.execute(
        sa_delete(Session).where(Session.curriculum_id == curriculum_id)
    )
    # 3) Skill model + concept edges keyed off this curriculum's concepts.
    if concept_ids:
        await session.execute(
            sa_delete(SkillModel).where(SkillModel.concept_id.in_(concept_ids))
        )
        await session.execute(
            sa_delete(ConceptEdge).where(ConceptEdge.source_id.in_(concept_ids))
        )
        await session.execute(
            sa_delete(ConceptEdge).where(ConceptEdge.target_id.in_(concept_ids))
        )
    # 4) Direct children of the curriculum.
    await session.execute(
        sa_delete(Checkpoint).where(Checkpoint.curriculum_id == curriculum_id)
    )
    await session.execute(
        sa_delete(Concept).where(Concept.curriculum_id == curriculum_id)
    )
    await session.execute(
        sa_delete(Segment).where(Segment.curriculum_id == curriculum_id)
    )
    await session.execute(
        sa_delete(Artifact).where(Artifact.curriculum_id == curriculum_id)
    )


@router.get("", response_model=List[Dict[str, Any]])
async def list_curricula(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant_id = current_user.tenant_id
    set_tenant_context(str(tenant_id))
    # Per-user scope (Block A follow-up): show this learner's own curricula.
    # Legacy rows with a NULL owner (pre-migration) stay visible within the
    # tenant so nothing silently disappears after the user_id backfill.
    stmt = (
        select(Curriculum)
        .where(
            Curriculum.tenant_id == tenant_id,
            or_(
                Curriculum.user_id == current_user.id,
                Curriculum.user_id.is_(None),
            ),
        )
        .order_by(Curriculum.created_at.desc())
    )
    result = await session.execute(stmt)
    curricula = result.scalars().all()

    # Feature 9 — per-card completion %. Derived from the learner's furthest
    # watched timestamp (Session.max_watched_ts) over the curriculum duration.
    # Best-effort: falls back to 0 when there is no session/duration yet, and
    # never fails the list response (max_watched_ts is an additive column).
    progress_map: Dict[int, float] = {}
    with contextlib.suppress(Exception):
        cur_ids = [c.id for c in curricula]
        if cur_ids:
            sess_rows = (
                await session.execute(
                    select(
                        Session.curriculum_id,
                        func.max(func.coalesce(Session.max_watched_ts, 0.0)),
                    )
                    .where(
                        Session.user_id == current_user.id,
                        Session.curriculum_id.in_(cur_ids),
                    )
                    .group_by(Session.curriculum_id)
                )
            ).all()
            watched_by_cur = {int(cid): float(mw or 0.0) for cid, mw in sess_rows}
            for c in curricula:
                dur = float(c.duration or 0.0)
                watched = watched_by_cur.get(c.id, 0.0)
                if dur > 0:
                    progress_map[c.id] = max(0.0, min(100.0, round(watched / dur * 100)))

    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "recap_status": c.recap_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "ready_at": c.ready_at.isoformat() if c.ready_at else None,
            "progress": progress_map.get(c.id, 0.0),
        }
        for c in curricula
    ]


@router.post("", response_model=Dict[str, Any])
async def create_curriculum(
    data: CurriculumCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        # Duplicate validation (per-user): if this learner already has a READY
        # curriculum for the same YouTube video, block the duplicate generation
        # and let the frontend surface an informative modal. Failed curricula
        # are NOT treated as duplicates so the user can retry. Non-YouTube URLs
        # (no extractable video id) skip the check. Scoped to the individual
        # user_id so two learners in a tenant can each keep their own instance.
        video_id = _extract_youtube_id(data.video_url)
        if video_id:
            existing = await _find_existing_ready_curriculum(
                session, tenant_id, current_user.id, video_id
            )
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "duplicate_curriculum",
                        "message": (
                            "This video is already in your workspace as "
                            f"\u201c{existing.title}\u201d."
                        ),
                        "curriculum_id": existing.id,
                    },
                )

        curriculum = Curriculum(
            tenant_id=tenant_id,
            user_id=current_user.id,
            title=data.title or "Untitled",
            source_ref=data.video_url,
            source_type="youtube" if video_id else "upload",
        )
        session.add(curriculum)
        await session.commit()
        await session.refresh(curriculum)

        # Run processing in background (dispatches the Celery task).
        asyncio.create_task(process_video(curriculum.id, data.video_url, tenant_id))

        return {"curriculum_id": curriculum.id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_curriculum: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.post("/upload", response_model=Dict[str, Any])
async def upload_curriculum(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Ingest a locally-uploaded video file (Phase 2).

    Streams the raw upload to MinIO at
    ``tenants/<tid>/curricula/<cid>/source_video<ext>``, creates the Curriculum
    row with ``source_type="upload"`` and ``source_ref=<s3 key>``, then
    dispatches the same ``generate_curriculum`` pipeline the YouTube path uses —
    the worker routes on the ref shape (S3 key → local-file ingest). The
    uploaded object is retained in MinIO so the HTML5 player can stream it.
    """
    from ice_shared.s3 import get_s3_client, tenant_prefix
    from ice_shared import settings as _settings

    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        # ── Server-side validation: extension + size ──────────────────────
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        allowed = {
            e.strip().lower()
            for e in _settings.settings.pipeline.upload_allowed_exts.split(",")
            if e.strip()
        }
        if ext not in allowed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type {ext or '(none)'}. Allowed: "
                    + ", ".join(sorted(allowed))
                ),
            )

        max_bytes = int(_settings.settings.pipeline.upload_max_bytes)

        # ── Create the curriculum row first so we have an id for the key ──
        curriculum = Curriculum(
            tenant_id=tenant_id,
            user_id=current_user.id,
            title=title or os.path.splitext(os.path.basename(filename))[0] or "Uploaded video",
            source_type="upload",
            source_ref=None,  # set below once the S3 key is known
            status=CurriculumStatus.queued,
        )
        session.add(curriculum)
        await session.commit()
        await session.refresh(curriculum)

        s3_key = (
            f"{tenant_prefix(tenant_id)}curricula/{curriculum.id}/source_video{ext}"
        )

        # ── Stream the upload to a temp file in bounded chunks (size-guarded),
        # then upload to MinIO off the event loop ─────────────────────────
        s3 = get_s3_client()
        bucket = _settings.settings.s3.bucket
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name
                total = 0
                while True:
                    chunk = await file.read(1024 * 1024)  # 1 MiB
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "File exceeds the maximum allowed size "
                                f"({max_bytes // (1024 * 1024)} MiB)."
                            ),
                        )
                    tmp.write(chunk)
            content_type = file.content_type or "application/octet-stream"
            await asyncio.to_thread(
                s3.upload_file,
                tmp_path,
                bucket,
                s3_key,
                {"ContentType": content_type},
            )
        finally:
            if tmp_path:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

        # Persist the resolved S3 key as the source ref, then dispatch.
        curriculum.source_ref = s3_key
        await session.commit()

        asyncio.create_task(process_video(curriculum.id, s3_key, tenant_id))

        return {"curriculum_id": curriculum.id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error in upload_curriculum: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/evaluate")
async def evaluate(
    payload: EvaluateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(str(current_user.tenant_id))

        cp_stmt = select(Checkpoint).where(Checkpoint.id == payload.checkpoint_id)
        cp_res = await session.execute(cp_stmt)
        cp = cp_res.scalar_one_or_none()
        if not cp:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        # Load the exercise so we can validate the answer against its payload.
        ex_stmt = select(Exercise).where(Exercise.checkpoint_id == cp.id)
        ex_res = await session.execute(ex_stmt)
        exercise = ex_res.scalar_one_or_none()

        answer = (payload.answer or "").strip()

        # Answers lock after the first attempt (Answer 2). If the learner has
        # already submitted this checkpoint, return the persisted verdict
        # instead of re-grading — this survives reloads and blocks re-dos.
        prior = await _get_checkpoint_attempt(session, current_user.id, cp.id)
        if prior is not None:
            return {
                "status": "ok",
                "passed": prior.status == "correct",
                "locked": True,
                "answer": prior.answer or "",
            }

        if exercise is None:
            # No exercise generated yet; fall back to non-empty check.
            return {"status": "ok", "passed": bool(answer)}

        ex_type = exercise.type.value if exercise.type else ""
        data: Dict[str, Any] = exercise.payload or {}

        extra: Dict[str, Any] = {}

        if ex_type == "mcq":
            options = data.get("options") or []
            answer_idx = data.get("answer_idx", data.get("answer_index"))
            try:
                correct = options[int(answer_idx)] if answer_idx is not None else None
            except (IndexError, TypeError, ValueError):
                correct = None
            passed = bool(answer) and answer == correct
        elif ex_type == "conceptual":
            reference = data.get("reference_answer") or ""
            min_sim = float(data.get("min_similarity", 0.7) or 0.7)
            ratio = SequenceMatcher(None, answer.lower(), reference.lower()).ratio()
            passed = bool(answer) and bool(reference) and ratio >= min_sim
        elif ex_type in ("coding", "debug"):
            # M9: actually execute the submission against the exercise's
            # hidden (+ visible) tests. Backend gated by SANDBOX_BACKEND inside
            # run_sandbox; when the sandbox is unavailable it falls back to a
            # local subprocess. Run off the event loop so we never block it.
            graded = await asyncio.to_thread(
                _evaluate_code_submission, answer, data, ex_type
            )
            passed = bool(graded.get("passed"))
            extra = {
                "stdout": graded.get("stdout", ""),
                "stderr": graded.get("stderr", ""),
            }
            if "tests_passed" in graded:
                extra["tests_passed"] = graded["tests_passed"]
                extra["tests_total"] = graded["tests_total"]
        else:
            passed = bool(answer)

        # M11: fold this attempt into the learner's skill model (best-effort;
        # never breaks the eval response). M10 adjusts next-checkpoint difficulty.
        await _update_skill_model(
            session, current_user.id, cp, exercise, passed
        )

        # Persist the attempt so the marker + locked state survive reloads.
        await _record_checkpoint_attempt(
            session, current_user.id, cp.id, passed, answer
        )

        return {"status": "ok", "passed": passed, **extra}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Evaluation error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{curriculum_id}/recap")
async def generate_recap(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        if curriculum.recap_status == "processing":
            raise HTTPException(status_code=409, detail="Recap is already generating")
            
        curriculum.recap_status = "processing"
        await session.commit()

        # Dispatch background task
        asyncio.create_task(trigger_recap(curriculum.id, tenant_id))

        return {"status": "processing"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_recap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{curriculum_id}")
async def delete_curriculum(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        tenant_id = current_user.tenant_id
        set_tenant_context(str(tenant_id))

        # Ownership check: only the owning user (or legacy rows with no owner)
        # within the tenant may delete. Filtering on tenant_id prevents
        # cross-tenant deletion; the user_id clause prevents one learner from
        # deleting another learner's instance in a shared tenant. Legacy rows
        # (user_id NULL, pre-migration) remain deletable by any tenant member.
        stmt = select(Curriculum).where(
            Curriculum.id == curriculum_id,
            Curriculum.tenant_id == tenant_id,
            or_(Curriculum.user_id == current_user.id, Curriculum.user_id.is_(None)),
        )
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        # Explicit, ordered cascade. DB-level ON DELETE CASCADE only fires when
        # the driver enforces FKs (Postgres always; SQLite only with
        # PRAGMA foreign_keys=ON, now enabled in db.py). We delete children
        # explicitly so cleanup is correct + identical on BOTH backends and so
        # per-user tables keyed off checkpoints/concepts (checkpoint_attempts,
        # skill_model, eval_results, session_events) are fully purged.
        await _cascade_delete_curriculum(session, curriculum_id)

        await session.delete(curriculum)
        await session.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting curriculum: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _get_or_create_session(
    session: AsyncSession, user_id: int, curriculum_id: int
):
    """Return the learner's Session row for this curriculum, creating it once."""
    stmt = select(Session).where(
        Session.user_id == user_id,
        Session.curriculum_id == curriculum_id,
    )
    row = (await session.execute(stmt)).scalars().first()
    if row is None:
        row = Session(user_id=user_id, curriculum_id=curriculum_id, resume_ts=0.0)
        session.add(row)
        await session.flush()
    return row


@router.get("/{curriculum_id}/progress", response_model=Dict[str, Any])
async def get_progress(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the learner's resume position + max-watched timestamp so the
    player can resume where they left off and enforce the anti-scrub ceiling
    (Feature 7)."""
    set_tenant_context(str(current_user.tenant_id))
    stmt = select(Session).where(
        Session.user_id == current_user.id,
        Session.curriculum_id == curriculum_id,
    )
    row = (await session.execute(stmt)).scalars().first()
    if row is None:
        return {"resume_ts": 0.0, "max_watched_ts": 0.0, "watched_seconds": 0.0}
    return {
        "resume_ts": float(row.resume_ts or 0.0),
        "max_watched_ts": float(getattr(row, "max_watched_ts", 0.0) or 0.0),
        "watched_seconds": float(getattr(row, "watched_seconds", 0.0) or 0.0),
    }


@router.post("/{curriculum_id}/progress", response_model=Dict[str, Any])
async def post_progress(
    curriculum_id: int,
    ping: ProgressPing,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Heartbeat: persist playback position + accumulate real watch-time.

    ``watched_seconds`` accrues from the per-ping ``watched_delta`` (actual
    playback time) rather than crediting the full video length, so dashboard
    hours reflect genuine engagement (Feature 7). ``max_watched_ts`` is
    monotonic — it only ever increases — and backs the forward-scrub lockout.
    """
    set_tenant_context(str(current_user.tenant_id))
    try:
        row = await _get_or_create_session(session, current_user.id, curriculum_id)
        row.resume_ts = max(0.0, float(ping.position or 0.0))
        prior_max = float(getattr(row, "max_watched_ts", 0.0) or 0.0)
        new_max = max(prior_max, float(ping.max_watched or 0.0), row.resume_ts)
        with contextlib.suppress(Exception):
            row.max_watched_ts = new_max
            delta = max(0.0, float(ping.watched_delta or 0.0))
            # Clamp a single delta so a backgrounded tab can't inflate hours.
            delta = min(delta, 60.0)
            row.watched_seconds = float(getattr(row, "watched_seconds", 0.0) or 0.0) + delta
        await session.commit()
        return {
            "resume_ts": row.resume_ts,
            "max_watched_ts": float(getattr(row, "max_watched_ts", new_max) or new_max),
            "watched_seconds": float(getattr(row, "watched_seconds", 0.0) or 0.0),
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"post_progress error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save progress")


@router.get("/{curriculum_id}", response_model=Dict[str, Any])
async def get_curriculum(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(str(current_user.tenant_id))

        # Fetch curriculum
        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        # Fetch related segments, concepts, checkpoints
        seg_stmt = select(Segment).where(Segment.curriculum_id == curriculum_id)
        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        conc_stmt = select(Concept).where(Concept.curriculum_id == curriculum_id)
        conc_result = await session.execute(conc_stmt)
        concepts = conc_result.scalars().all()

        cp_stmt = select(Checkpoint).where(Checkpoint.curriculum_id == curriculum_id)
        cp_result = await session.execute(cp_stmt)
        checkpoints = cp_result.scalars().all()

        # Fetch exercises for these checkpoints
        if checkpoints:
            cp_ids = [cp.id for cp in checkpoints]
            ex_stmt = select(Exercise).where(Exercise.checkpoint_id.in_(cp_ids))
            ex_result = await session.execute(ex_stmt)
            exercises = ex_result.scalars().all()
            exercise_map = {ex.checkpoint_id: ex for ex in exercises}
        else:
            exercise_map = {}

        # Fetch this learner's persisted checkpoint attempts (Answer 2) so the
        # frontend can hydrate the donut/markers + locked review after reload.
        attempt_map: Dict[int, Any] = {}
        if checkpoints:
            from ice_api.models import CheckpointAttempt

            att_stmt = select(CheckpointAttempt).where(
                CheckpointAttempt.user_id == current_user.id,
                CheckpointAttempt.checkpoint_id.in_(cp_ids),
            )
            att_result = await session.execute(att_stmt)
            attempt_map = {a.checkpoint_id: a for a in att_result.scalars().all()}

        return {
            "id": curriculum.id,
            "title": curriculum.title,
            "created_at": curriculum.created_at.isoformat() if curriculum.created_at else None,
            "status": curriculum.status,
            "recap_status": curriculum.recap_status,
            "recap_url": curriculum.recap_url,
            "recap_transcript_html": curriculum.recap_transcript_html,
            "signal_status": curriculum.signal_status,
            "signal_video_url": curriculum.signal_video_url,
            "ready_at": curriculum.ready_at.isoformat() if curriculum.ready_at else None,
            "video_url": curriculum.source_ref,
            "source_type": curriculum.source_type,
            "duration": curriculum.duration,
            "segments": [
                {
                    "id": seg.id,
                    "title": seg.title,
                    "summary": seg.summary,
                    "start": seg.start_time,
                    "end": seg.end_time,
                }
                for seg in segments
            ],
            "concepts": [
                {
                    "id": conc.id,
                    "label": conc.label,
                    "description": conc.description,
                    "difficulty": conc.difficulty,
                }
                for conc in concepts
            ],
            "checkpoints": [
                {
                    "id": cp.id,
                    "ts": cp.ts,
                    "segment_id": cp.segment_id,
                    "concept_id": cp.concept_id,
                    "exercise_type": cp.exercise_type,
                    "difficulty": cp.difficulty,
                    "exercise": _exercise_payload(exercise_map.get(cp.id)),
                    # Persisted attempt state (Answer 2): status hydrates the
                    # donut markers; submitted_answer pre-fills locked review.
                    "status": (attempt_map[cp.id].status if cp.id in attempt_map else None),
                    "submitted_answer": (
                        attempt_map[cp.id].answer if cp.id in attempt_map else None
                    ),
                }
                for cp in checkpoints
            ],
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{curriculum_id}/video", response_model=Dict[str, Any])
async def get_upload_video_url(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return a presigned MinIO URL for a locally-uploaded source video.

    Only applies to ``source_type=="upload"`` rows (YouTube rows are streamed
    directly by the react-youtube player and never hit this endpoint). The URL
    is generated against ``MINIO_EXTERNAL_ENDPOINT`` so the browser can reach
    MinIO from outside the docker network (same robust external-client pattern
    used by the recap task).
    """
    from ice_shared import settings as _settings

    try:
        set_tenant_context(str(current_user.tenant_id))

        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        if curriculum.source_type != "upload":
            raise HTTPException(
                status_code=400,
                detail="Video URL only available for uploaded curricula",
            )

        s3_key = curriculum.source_ref
        if not s3_key:
            raise HTTPException(status_code=404, detail="No source video available")

        # Robust external-client pattern (mirrors recap.py:378-401): sign the
        # URL against the browser-reachable external endpoint so playback works
        # from outside the docker network.
        external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000")

        import boto3
        from botocore.config import Config

        external_s3 = boto3.client(
            "s3",
            endpoint_url=external_endpoint,
            aws_access_key_id=_settings.settings.s3.access_key,
            aws_secret_access_key=_settings.settings.s3.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        url = external_s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": _settings.settings.s3.bucket, "Key": s3_key},
            ExpiresIn=7 * 24 * 3600,
        )

        return {"video_url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating video URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{curriculum_id}/signal")
async def start_signal_video(
    curriculum_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        set_tenant_context(str(current_user.tenant_id))
        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Not found")

        c.signal_status = "queued"
        await session.commit()
        
        await trigger_signal(curriculum_id, current_user.tenant_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error starting signal video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
