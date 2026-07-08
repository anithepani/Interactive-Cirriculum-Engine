"""M8 Test Generation & Validation - core generator.

Takes a coding exercise (with ``reference_solution`` + optional ``starter``) and
produces validated visible + hidden tests via a five-stage pipeline:

  1. Candidate test generation - the LLM emits assert-statement strings
     (visible + hidden) conditioned on the exercise prompt + reference solution.
  2. Reference pass check - every generated test must pass on the provided
     reference solution (executed in a local subprocess).
  3. CodeT self-consistency (Chen 2022, "Code Generation with Generated Tests") -
     generate K independent reference solutions and verify the candidate tests
     pass on the majority. This filters tests that overfit one solution's quirks.
     Majority voting (rather than strict unanimity) is used because some
     LLM-generated solutions may themselves be buggy; the principle - agreement
     across independent solutions - is preserved.
  4. Mutation testing - the LLM generates K buggy mutants tagged with common
     bug categories (off-by-one, missing edge case, wrong operator, etc.); the
     candidate tests must catch (kill) them. ``mutation_score = killed / total``.
  5. Validation gate - ``validation_passed`` is True iff the reference passes AND
     CodeT consensus holds AND ``mutation_score >= MUTATION_THRESHOLD``. On
     failure the whole pipeline retries up to ``MAX_RETRIES`` times.

Test execution writes ``solution + "\\n" + tests`` to a temp module and runs it
with the current interpreter (exit 0 = pass). The backend is isolated behind
``_run_tests`` so judge0 can replace it later (Zubair, sandbox integration).

Plain-dict I/O is used throughout, consistent with M2/M4/M5/M6/M7.

Lead: Aryan. Support: Zubair (sandbox).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from ice_llm import LLMClient, get_client

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PROMPT_DIR = _REPO_ROOT / "prompt-library" / "test_gen"

_SYSTEM = (
    "You are an expert at designing and validating Python test cases. You MUST "
    "respond with ONLY a single valid JSON object - no markdown fences, no prose, "
    "no explanation. The JSON must conform exactly to the requested schema."
)

MAX_RETRIES = 3
CODET_K = 3
MUTANT_K = 4
MUTATION_THRESHOLD = 0.6
RUN_TIMEOUT = 10

_BUG_CATEGORIES = [
    "off-by-one error (e.g. < vs <=, wrong range endpoint)",
    "missing edge case (e.g. empty input, single element, zero)",
    "wrong operator or comparison direction",
    "incorrect return value or type",
    "forgotten case in a conditional branch",
]

_MUTANT_SYSTEM = (
    "You are a software engineer producing buggy variants of a correct solution "
    "for mutation testing. Each variant must be valid Python that compiles but "
    "contains exactly ONE subtle bug that changes the output for at least some "
    "inputs. Respond with ONLY a JSON object: "
    '{"mutants": [{"code": "...", "bug": "short description"}, ...]}. '
    "No markdown fences, no prose."
)

_SOLUTION_SYSTEM = (
    "You are an expert Python programmer. Write a correct, independent solution "
    "to the given problem. It must define the same function(s) as the starter so "
    "the existing tests can call it. Respond with ONLY a JSON object: "
    '{"code": "..."} where the value is the full Python source. '
    "No markdown fences, no prose."
)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def generate_tests(exercise: dict[str, Any]) -> dict[str, Any]:
    """Generate validated visible + hidden tests for a coding exercise.

    Args:
        exercise: A coding exercise dict (the ``CodingExercise`` envelope from
            ``ice_contracts``). Must contain ``coding.reference_solution``;
            ``coding.starter``, ``coding.constraints``, ``prompt`` and
            ``difficulty`` are used when present.

    Returns:
        ``{"tests_visible": list[str], "tests_hidden": list[str],
        "validation_passed": bool, "mutation_score": float}``.

        On success ``validation_passed`` is True and the tests are the validated
        set from the passing attempt. On exhaustion of retries the best (last)
        attempt's tests are returned with ``validation_passed`` False.
    """
    coding = exercise.get("coding") or {}
    reference_solution = coding.get("reference_solution", "")
    starter = coding.get("starter", "")
    constraints = coding.get("constraints", []) or []
    prompt_text = exercise.get("prompt", "")
    difficulty = int(exercise.get("difficulty", 3))

    if not reference_solution:
        logger.error(
            "generate_tests: no reference_solution in exercise %s", exercise.get("id", "?")
        )
        return _empty_result()

    client = get_client()

    last_result: dict[str, Any] = _empty_result()

    for attempt in range(MAX_RETRIES + 1):
        candidate = _generate_candidate_tests(
            client, prompt_text, reference_solution, starter, constraints, difficulty
        )
        if candidate is None:
            logger.warning(
                "Attempt %d/%d: candidate test generation failed", attempt + 1, MAX_RETRIES + 1
            )
            continue

        tests_visible = [t for t in candidate.get("tests_visible", []) if t.strip()]
        tests_hidden = [t for t in candidate.get("tests_hidden", []) if t.strip()]
        all_tests = tests_visible + tests_hidden
        if not all_tests:
            logger.warning("Attempt %d/%d: no tests generated", attempt + 1, MAX_RETRIES + 1)
            continue

        ref_passes, ref_err = _run_tests(reference_solution, all_tests)
        if not ref_passes:
            logger.warning(
                "Attempt %d/%d: tests fail on reference solution: %s",
                attempt + 1,
                MAX_RETRIES + 1,
                (ref_err or "")[:200],
            )
            last_result = {
                "tests_visible": tests_visible,
                "tests_hidden": tests_hidden,
                "validation_passed": False,
                "mutation_score": 0.0,
            }
            continue

        codet_passed = _codet_consensus(client, prompt_text, starter, constraints, all_tests)

        mutation_score = _mutation_testing(client, reference_solution, prompt_text, all_tests)

        validation_passed = codet_passed and mutation_score >= MUTATION_THRESHOLD
        last_result = {
            "tests_visible": tests_visible,
            "tests_hidden": tests_hidden,
            "validation_passed": validation_passed,
            "mutation_score": round(mutation_score, 4),
        }

        if validation_passed:
            logger.info(
                "Validation passed on attempt %d (codet=ok, mutation_score=%.2f)",
                attempt + 1,
                mutation_score,
            )
            return last_result

        logger.warning(
            "Attempt %d/%d: validation failed (codet=%s, mutation_score=%.2f)",
            attempt + 1,
            MAX_RETRIES + 1,
            codet_passed,
            mutation_score,
        )

    logger.error(
        "Validation failed after %d attempts for exercise %s",
        MAX_RETRIES + 1,
        exercise.get("id", "?"),
    )
    return last_result


# --------------------------------------------------------------------------- #
# Stage 1 - candidate test generation
# --------------------------------------------------------------------------- #


def _generate_candidate_tests(
    client: LLMClient,
    prompt_text: str,
    reference_solution: str,
    starter: str,
    constraints: list[str],
    difficulty: int,
) -> dict[str, Any] | None:
    """Ask the LLM for a candidate set of visible + hidden assert statements."""
    template = _load_template("coding")
    variables = {
        "prompt": prompt_text,
        "reference_solution": reference_solution,
        "starter": starter or "(no starter provided)",
        "constraints": _fmt_constraints(constraints),
        "difficulty": difficulty,
    }
    rendered = _render(template, variables)

    few_shot = _load_few_shot("coding")
    if few_shot:
        rendered += "\n\n## Example output\n```json\n" + few_shot + "\n```"
    rendered += "\n\nRespond with ONLY a JSON object. No markdown fences, no prose."

    try:
        raw = client.complete(rendered, system=_SYSTEM)
        parsed = _parse_json(raw)
        if "tests_visible" in parsed and "tests_hidden" in parsed:
            return parsed
        logger.warning("Candidate tests missing required keys: %s", list(parsed.keys()))
        return None
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Candidate test generation parse error: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Stage 3 - CodeT self-consistency
# --------------------------------------------------------------------------- #


def _codet_consensus(
    client: LLMClient,
    prompt_text: str,
    starter: str,
    constraints: list[str],
    all_tests: list[str],
) -> bool:
    """Verify candidate tests pass on the majority of independent solutions.

    Generates ``CODET_K`` alternative reference solutions; tests must pass on at
    least the majority of the valid (compiling) ones. With fewer than 2 valid
    solutions consensus cannot be established and the check is skipped (passes).
    """
    alt_solutions = _generate_reference_solutions(
        client, prompt_text, starter, constraints, k=CODET_K
    )
    valid = [s for s in alt_solutions if _compiles(s)]
    if len(valid) < 2:
        logger.info("CodeT: too few valid alt solutions (%d); skipping consensus", len(valid))
        return True

    passed = 0
    for sol in valid:
        ok, _ = _run_tests(sol, all_tests)
        if ok:
            passed += 1

    majority = passed >= (len(valid) // 2 + 1)
    logger.info(
        "CodeT: %d/%d alt solutions passed tests (majority=%s)", passed, len(valid), majority
    )
    return majority


def _generate_reference_solutions(
    client: LLMClient,
    prompt_text: str,
    starter: str,
    constraints: list[str],
    k: int = CODET_K,
) -> list[str]:
    """Generate ``k`` independent reference solutions via the LLM."""
    prompt = (
        "Write a correct Python solution to the following problem. It must define "
        "the same function(s) as the starter so the existing tests can call it.\n\n"
        f"## Problem\n{prompt_text}\n\n"
        f"## Starter / signature\n```python\n{starter or '(none)'}\n```\n\n"
        f"## Constraints\n{_fmt_constraints(constraints)}\n\n"
        'Respond with ONLY JSON: {"code": "<full python source>"}.'
    )
    solutions: list[str] = []
    for _ in range(k):
        try:
            raw = client.complete(prompt, system=_SOLUTION_SYSTEM)
            parsed = _parse_json(raw)
            code = str(parsed.get("code", ""))
            if code and _compiles(code):
                solutions.append(code)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Reference solution generation error: %s", exc)
    return solutions


# --------------------------------------------------------------------------- #
# Stage 4 - mutation testing
# --------------------------------------------------------------------------- #


def _mutation_testing(
    client: LLMClient,
    reference_solution: str,
    prompt_text: str,
    all_tests: list[str],
) -> float:
    """Run mutation testing: generate buggy mutants, count how many tests kill.

    Returns ``killed / total`` over syntactically-valid mutants. Mutants that do
    not compile are skipped (not counted).
    """
    mutants = _generate_mutants(client, reference_solution, prompt_text, k=MUTANT_K)

    killed = 0
    total = 0
    for m in mutants:
        code = str(m.get("code", ""))
        if not _compiles(code):
            logger.debug("Skipping non-compiling mutant: %s", m.get("bug", "?"))
            continue
        total += 1
        passed, _ = _run_tests(code, all_tests)
        if not passed:
            killed += 1

    score = killed / total if total > 0 else 0.0
    logger.info("Mutation testing: killed %d/%d mutants (score=%.2f)", killed, total, score)
    return score


def _generate_mutants(
    client: LLMClient,
    reference_solution: str,
    prompt_text: str,
    k: int = MUTANT_K,
) -> list[dict[str, Any]]:
    """Ask the LLM for ``k`` buggy mutants of the reference solution."""
    categories = _BUG_CATEGORIES[:k]
    cats_text = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(categories))
    prompt = (
        "Produce buggy mutants of the following correct Python solution for "
        "mutation testing. Each mutant must be a FULL Python source that compiles "
        "but contains exactly ONE subtle bug from these categories:\n"
        f"{cats_text}\n\n"
        f"## Problem\n{prompt_text}\n\n"
        f"## Correct solution\n```python\n{reference_solution}\n```\n\n"
        f"Generate {len(categories)} mutants (one per category listed). "
        "Respond with ONLY JSON: "
        '{"mutants": [{"code": "...", "bug": "..."}]}.'
    )
    try:
        raw = client.complete(prompt, system=_MUTANT_SYSTEM)
        parsed = _parse_json(raw)
        mutants = parsed.get("mutants", [])
        if isinstance(mutants, list):
            return [m for m in mutants if isinstance(m, dict) and m.get("code")]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Mutant generation error: %s", exc)
    return []


# --------------------------------------------------------------------------- #
# Execution backend (pluggable - judge0 can replace _run_tests later)
# --------------------------------------------------------------------------- #


def _run_tests(solution: str, tests: list[str], timeout: int = RUN_TIMEOUT) -> tuple[bool, str]:
    """Execute ``solution`` + ``tests`` in a subprocess; exit 0 == pass.

    The program is ``<solution>\\n\\n<each assert>``. A non-zero exit (assertion
    failure, exception, timeout) means the tests caught a bug (or the solution is
    wrong). Returns ``(passed, stderr)``.
    """
    program = solution.rstrip() + "\n\n" + "\n".join(t for t in tests if t.strip()) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(program)
        path = f.name
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except OSError as exc:
        return False, f"EXEC_ERROR: {exc}"
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def _compiles(code: str) -> bool:
    """Return True if ``code`` is syntactically valid Python."""
    try:
        compile(code, "<candidate>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


# --------------------------------------------------------------------------- #
# Prompt loading + rendering helpers (mirror M7 ice_exercise_gen)
# --------------------------------------------------------------------------- #


def _load_template(subdir: str) -> str:
    path = _PROMPT_DIR / subdir / "template.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_few_shot(subdir: str) -> str | None:
    path = _PROMPT_DIR / subdir / "few_shot.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data and isinstance(data, list) and len(data) > 0:
            output = data[0].get("output", {})
            return json.dumps(output, indent=2)
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Could not parse few_shot for %s", subdir)
    return None


def _render(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace("{{ " + key + " }}", str(value))
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        if start != -1:
            text = text[start:]
    return cast(dict[str, Any], json.loads(text))


def _fmt_constraints(constraints: list[str]) -> str:
    if not constraints:
        return "(none)"
    return "\n".join(f"- {c}" for c in constraints)


def _empty_result() -> dict[str, Any]:
    return {
        "tests_visible": [],
        "tests_hidden": [],
        "validation_passed": False,
        "mutation_score": 0.0,
    }
