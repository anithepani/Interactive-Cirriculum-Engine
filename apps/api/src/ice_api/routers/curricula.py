from __future__ import annotations
import sys
import os
import subprocess
import tempfile
import contextlib
import logging
import asyncio
import traceback
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ice_shared.db import get_session, set_tenant_context
from ice_api.auth_utils import get_current_user
from ice_api.models import (
    Curriculum,
    Tenant,
    Segment,
    Concept,
    Checkpoint,
    Exercise,
    User,
    SkillModel,
)
from ice_api.process import process_video, trigger_recap

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


def _evaluate_code_submission(answer: str, data: Dict[str, Any], ex_type: str) -> Dict[str, Any]:
    """Execute learner code against hidden tests; return passed + stdout/stderr."""
    tests = _collect_tests(data, ex_type)
    language = str(data.get("language", "python") or "python")

    if not answer.strip():
        return {"status": "ok", "passed": False, "stdout": "", "stderr": "No code submitted."}

    # Fix 1: guard against self-inconsistent LLM-generated tests by keeping only
    # those the reference solution itself passes.
    if tests:
        tests = _validate_tests_against_reference(tests, data, language)

    if not tests:
        # No (valid) stored tests: run the code once to surface output; pass if
        # it runs cleanly (mirrors /execute's exit-0 semantics). Non-regressive:
        # stricter than the old "non-empty == pass" only when execution errors.
        ok, out, err = _run_code_against_test(answer, "", language)
        return {"status": "ok", "passed": ok, "stdout": out, "stderr": err}

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


router = APIRouter(prefix="/api/v1/curricula", tags=["curricula"])


class CurriculumCreate(BaseModel):
    video_url: str
    title: Optional[str] = None


class EvaluateRequest(BaseModel):
    checkpoint_id: int
    answer: str


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


@router.get("", response_model=List[Dict[str, Any]])
async def list_curricula(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant_id = current_user.tenant_id
    set_tenant_context(str(tenant_id))
    stmt = select(Curriculum).where(Curriculum.tenant_id == tenant_id).order_by(Curriculum.created_at.desc())
    result = await session.execute(stmt)
    curricula = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "recap_status": c.recap_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "ready_at": c.ready_at.isoformat() if c.ready_at else None,
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

        curriculum = Curriculum(
            tenant_id=tenant_id,
            title=data.title or "Untitled",
            source_ref=data.video_url,
        )
        session.add(curriculum)
        await session.commit()
        await session.refresh(curriculum)

        # Run processing in background (dispatches the Celery task).
        asyncio.create_task(process_video(curriculum.id, data.video_url, tenant_id))

        return {"curriculum_id": curriculum.id, "status": "queued"}

    except Exception as e:
        logger.error(f"Error in create_curriculum: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=traceback.format_exc())


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

        stmt = select(Curriculum).where(Curriculum.id == curriculum_id)
        result = await session.execute(stmt)
        curriculum = result.scalar_one_or_none()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        await session.delete(curriculum)
        await session.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error deleting curriculum: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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

        return {
            "id": curriculum.id,
            "title": curriculum.title,
            "created_at": curriculum.created_at.isoformat() if curriculum.created_at else None,
            "status": curriculum.status,
            "recap_status": curriculum.recap_status,
            "recap_url": curriculum.recap_url,
            "recap_transcript_html": curriculum.recap_transcript_html,
            "ready_at": curriculum.ready_at.isoformat() if curriculum.ready_at else None,
            "video_url": curriculum.source_ref,
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
                }
                for cp in checkpoints
            ],
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
