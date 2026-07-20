"""M9 Answer Evaluation & Feedback Engine - core evaluator.

Grades a learner ``response`` against an ``exercise`` of any type and returns a
verdict, score, explanation, hints, and an anti-cheat flag.

Per-type strategy:
  - mcq        : exact match on ``answer_idx`` + distractor analytics (E13).
  - coding     : local-subprocess sandbox runs learner code against visible +
                 hidden tests; ``ruff`` static analysis; LLM-as-a-Judge rubric
                 (Zheng 2023) for partial credit / style / quality notes.
  - debug      : subprocess runs the corrected code against the hidden tests;
                 LLM-as-a-Judge grades the bug explanation.
  - conceptual : embedding similarity (sentence-transformers, token-overlap
                 fallback) vs the reference answer + LLM-as-a-Judge rubric.

Anti-cheat (E12): CodeBLEU-style similarity between the learner's code and the
instructor's extracted code (stored on ``exercise["context"]`` by M7). When the
similarity exceeds ``ANTICHEAT_THRESHOLD`` the attempt is flagged. CodeBLEU is
computed via the optional ``codebleu`` package when installed, otherwise a
built-in tree-sitter AST + n-gram BLEU blend is used.

Plain-dict I/O is used throughout (consistent with M2/M4/M5/M6/M7/M8); each
result dict is validated against ``ice_contracts.EvalResult``.

Response shapes:
  - mcq        : {"answer_idx": int}
  - coding     : {"code": str}
  - debug      : {"corrected_code": str, "explanation": str}
  - conceptual : {"answer": str}

Lead: Aryan. Support: Zubair (sandbox integration).
"""

from __future__ import annotations

import contextlib
import json
import logging
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from ice_contracts.eval_result import EvalResult
from ice_llm import LLMClient, get_client
from pydantic import TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PROMPT_DIR = _REPO_ROOT / "prompt-library" / "evaluation"

_SYSTEM = (
    "You are an expert programming instructor grading a submission. You MUST "
    "respond with ONLY a single valid JSON object - no markdown fences, no prose. "
    "The JSON must conform exactly to the requested schema."
)

# ---- thresholds & weights -------------------------------------------------
ANTICHEAT_THRESHOLD = 0.80
RUN_TIMEOUT = 10
RUFF_TIMEOUT = 10
_CODE_WEIGHT_TESTS = 0.6
_CODE_WEIGHT_LLM = 0.4
_DEBUG_WEIGHT_TESTS = 0.5
_DEBUG_WEIGHT_LLM = 0.5
_CONCEPT_WEIGHT_SIM = 0.4
_CONCEPT_WEIGHT_LLM = 0.6
_CONCEPT_PASS_SIM = 0.55
_CONCEPT_PASS_LLM = 0.6
_PARTIAL_THRESHOLD = 0.01

adapter: TypeAdapter[EvalResult] = TypeAdapter(EvalResult)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def evaluate(exercise: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Grade a learner response for any exercise type.

    Args:
        exercise: An exercise envelope dict (mcq/coding/debug/conceptual) as
            produced by M7. The instructor's extracted code (if any) lives on
            ``exercise["context"]`` and is used for anti-cheat.
        response: A learner response dict (see module docstring for shapes).

    Returns:
        ``{"verdict": "pass"|"fail"|"partial", "score": float,
        "explanation": str, "hints": list[str], "anti_cheat_flag": bool}``.
    """
    etype = exercise.get("type", "")
    try:
        if etype == "mcq":
            return _eval_mcq(exercise, response)
        if etype == "coding":
            return _eval_coding(exercise, response)
        if etype == "debug":
            return _eval_debug(exercise, response)
        if etype == "conceptual":
            return _eval_conceptual(exercise, response)
    except Exception as exc:
        logger.exception("evaluate: error grading %s exercise %s", etype, exercise.get("id", "?"))
        return _to_result("fail", 0.0, f"Evaluation error: {exc}", [], False, exercise)

    return _to_result("fail", 0.0, f"Unknown exercise type: {etype!r}", [], False, exercise)


# --------------------------------------------------------------------------- #
# MCQ
# --------------------------------------------------------------------------- #


def _eval_mcq(exercise: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Exact match on the chosen option; distractor analytics when wrong (E13)."""
    mcq = exercise.get("mcq") or {}
    options = mcq.get("options", []) or []
    correct_idx = int(mcq.get("answer_idx", -1))
    learner_idx = _coerce_int(
        response.get("answer_idx", response.get("choice", response.get("answer")))
    )

    anti_cheat = False
    hints: list[str] = []

    if learner_idx == correct_idx:
        verdict = "pass"
        score = 1.0
        explanation = "Correct option selected."
    else:
        verdict = "fail"
        score = 0.0
        chosen = options[learner_idx] if 0 <= learner_idx < len(options) else "(invalid)"
        correct = options[correct_idx] if 0 <= correct_idx < len(options) else "(unknown)"
        tags = mcq.get("distractor_tags", []) or []
        tag_note = ""
        if 0 <= learner_idx < len(tags):
            tag_note = f" This is a common misconception: {tags[learner_idx]}."
        explanation = f"Incorrect. You chose: {chosen!r}. Correct: {correct!r}.{tag_note}"
        hints.append("Revisit the concept and identify why the correct option holds.")

    return _to_result(verdict, score, explanation, hints, anti_cheat, exercise)


# --------------------------------------------------------------------------- #
# Coding
# --------------------------------------------------------------------------- #


def _eval_coding(exercise: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Sandbox tests + ruff static analysis + LLM-as-a-Judge + CodeBLEU anti-cheat."""
    coding = exercise.get("coding") or {}
    learner_code = str(response.get("code", "")).strip()
    if not learner_code:
        return _to_result("fail", 0.0, "No code submitted.", [], False, exercise)

    tests_visible = coding.get("tests_visible", []) or []
    tests_hidden = coding.get("tests_hidden", []) or []
    all_tests = list(tests_visible) + list(tests_hidden)

    passed, total, _err = _run_tests_counted(learner_code, all_tests)
    test_ratio = passed / total if total > 0 else 0.0

    ruff_issues = _ruff_check(learner_code)

    client = get_client()
    judge = _llm_judge(
        client,
        "judge_code",
        {
            "prompt": exercise.get("prompt", ""),
            "learner_code": learner_code,
            "tests": "\n".join(all_tests) or "(none)",
            "test_pass_ratio": f"{test_ratio:.2f}",
            "ruff_issues": ruff_issues or "none",
        },
    )
    llm_score = _clip(judge.get("score", test_ratio))
    llm_notes = str(judge.get("explanation", "")).strip()
    llm_hints = judge.get("hints", []) or []

    score = _clip(_CODE_WEIGHT_TESTS * test_ratio + _CODE_WEIGHT_LLM * llm_score)

    if test_ratio >= 1.0 and llm_score >= 0.5:
        verdict = "pass"
    elif test_ratio > 0.0 or llm_score > 0.0:
        verdict = "partial"
    else:
        verdict = "fail"

    parts = [f"Tests: {passed}/{total} passed (ratio {test_ratio:.2f})."]
    if ruff_issues and ruff_issues != "none":
        parts.append(f"Static analysis (ruff): {ruff_issues}.")
    if llm_notes:
        parts.append(f"Judge: {llm_notes}")
    explanation = " ".join(parts)

    instructor_code = exercise.get("context") or ""
    anti_cheat = _anticheat_flag(learner_code, instructor_code)
    if anti_cheat:
        hints_add = [
            "Your solution is very similar to the instructor's example - rework it in your own words."
        ]
        explanation += " Anti-cheat: submission is highly similar to the instructor's code (E12)."

    hints = list(llm_hints) + (hints_add if anti_cheat else [])
    return _to_result(verdict, score, explanation, hints, anti_cheat, exercise)


# --------------------------------------------------------------------------- #
# Debug
# --------------------------------------------------------------------------- #


def _eval_debug(exercise: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Run tests on corrected code + LLM-as-a-Judge on the bug explanation."""
    debug = exercise.get("debug") or {}
    corrected_code = str(response.get("corrected_code", "")).strip()
    learner_explanation = str(response.get("explanation", "")).strip()
    tests = debug.get("tests", []) or []

    if not corrected_code:
        return _to_result("fail", 0.0, "No corrected code submitted.", [], False, exercise)

    passed, total, _err = _run_tests_counted(corrected_code, tests)
    test_ratio = passed / total if total > 0 else 0.0

    client = get_client()
    judge = _llm_judge(
        client,
        "judge_debug",
        {
            "prompt": exercise.get("prompt", ""),
            "buggy_code": debug.get("buggy_code", ""),
            "bug_explanation": debug.get("bug_explanation", ""),
            "learner_explanation": learner_explanation or "(no explanation given)",
            "test_pass_ratio": f"{test_ratio:.2f}",
        },
    )
    llm_score = _clip(judge.get("score", test_ratio))
    llm_notes = str(judge.get("explanation", "")).strip()
    llm_hints = judge.get("hints", []) or []

    score = _clip(_DEBUG_WEIGHT_TESTS * test_ratio + _DEBUG_WEIGHT_LLM * llm_score)
    if test_ratio >= 1.0 and llm_score >= 0.5:
        verdict = "pass"
    elif test_ratio > 0.0 or llm_score > 0.0:
        verdict = "partial"
    else:
        verdict = "fail"

    explanation = f"Corrected code tests: {passed}/{total} passed (ratio {test_ratio:.2f})."
    if llm_notes:
        explanation += f" Explanation: {llm_notes}"

    instructor_code = exercise.get("context") or ""
    anti_cheat = _anticheat_flag(corrected_code, instructor_code)
    return _to_result(verdict, score, explanation, list(llm_hints), anti_cheat, exercise)


# --------------------------------------------------------------------------- #
# Conceptual
# --------------------------------------------------------------------------- #


def _eval_conceptual(exercise: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Embedding similarity + LLM-as-a-Judge rubric."""
    conceptual = exercise.get("conceptual") or {}
    reference_answer = str(conceptual.get("reference_answer", ""))
    rubric = conceptual.get("rubric", []) or []
    min_similarity = float(conceptual.get("min_similarity", 0.7))
    learner_answer = str(response.get("answer", "")).strip()

    if not learner_answer:
        return _to_result("fail", 0.0, "No answer submitted.", [], False, exercise)

    sim = _embedding_similarity(learner_answer, reference_answer)

    client = get_client()
    judge = _llm_judge(
        client,
        "judge_conceptual",
        {
            "prompt": exercise.get("prompt", ""),
            "reference_answer": reference_answer,
            "rubric": "\n".join(f"- {r}" for r in rubric) or "(none)",
            "learner_answer": learner_answer,
            "embedding_similarity": f"{sim:.2f}",
        },
    )
    llm_score = _clip(judge.get("score", sim))
    llm_notes = str(judge.get("explanation", "")).strip()
    llm_hints = judge.get("hints", []) or []

    score = _clip(_CONCEPT_WEIGHT_SIM * sim + _CONCEPT_WEIGHT_LLM * llm_score)
    if sim >= min_similarity and llm_score >= _CONCEPT_PASS_LLM:
        verdict = "pass"
    elif sim >= _CONCEPT_PASS_SIM or llm_score >= 0.4:
        verdict = "partial"
    else:
        verdict = "fail"

    explanation = (
        f"Embedding similarity: {sim:.2f} (threshold {min_similarity:.2f}). "
        f"Judge score: {llm_score:.2f}."
    )
    if llm_notes:
        explanation += f" {llm_notes}"
    return _to_result(verdict, score, explanation, list(llm_hints), False, exercise)


# --------------------------------------------------------------------------- #
# Execution backend (sandbox stub - judge0 can replace _run_tests_counted later)
# --------------------------------------------------------------------------- #


def _run_tests_counted(
    solution: str, tests: list[str], timeout: int = RUN_TIMEOUT
) -> tuple[int, int, str]:
    """Run each test independently against ``solution``; return (passed, total, err).

    Tests are executed one at a time so a single failing assertion does not abort
    the rest. Returns the count of passing tests. The full-suite error from the
    first failure is captured in ``err`` for diagnostics.
    """
    valid_tests = [t for t in tests if t and t.strip()]
    total = len(valid_tests)
    if total == 0:
        return 0, 0, ""
    passed = 0
    first_err = ""
    for test in valid_tests:
        ok, err = _run_one(solution, test, timeout)
        if ok:
            passed += 1
        elif not first_err:
            first_err = err
    return passed, total, first_err


def _run_one(solution: str, test: str, timeout: int) -> tuple[bool, str]:
    """Execute ``solution + "\\n" + test``; exit 0 == pass.

    Routes through the Judge0 sandbox when ``SANDBOX_BACKEND=judge0`` and the
    service is reachable; otherwise (default, or Judge0 down) falls back to the
    original local-subprocess path so behavior is unchanged when the sandbox is
    not configured (zero-regression).
    """
    program = solution.rstrip() + "\n\n" + test.strip() + "\n"

    # Judge0 path (opt-in, with automatic fallback to subprocess below).
    try:
        from ice_shared.judge0_client import run_sandbox

        sb = run_sandbox(program, language="python")
        if sb.backend == "judge0":
            return sb.passed, sb.stderr or ""
        # backend in {"subprocess", "unavailable"} -> fall through to local run.
    except Exception as exc:  # pragma: no cover - defensive: never break grading
        logger.debug("Judge0 sandbox unavailable, using local subprocess: %s", exc)

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


# --------------------------------------------------------------------------- #
# Static analysis (ruff)
# --------------------------------------------------------------------------- #


def _ruff_check(code: str, timeout: int = RUFF_TIMEOUT) -> str:
    """Run ``ruff check`` on the learner code; return a short summary of issues.

    Returns the string "none" when there are no issues. Uses the ruff binary
    located via ``ruff.find_ruff_bin()``.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        bin_path = _find_ruff_bin()
        if bin_path is None:
            return "none"
        result = subprocess.run(
            [bin_path, "check", "--output-format=json", "--exit-zero", path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        try:
            msgs = json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            return "unavailable"
        if not msgs:
            return "none"
        codes = sorted({str(m.get("code", "?")) for m in msgs})
        return ", ".join(codes)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("ruff check failed: %s", exc)
        return "none"
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def _find_ruff_bin() -> str | None:
    """Locate the ruff binary via its Python package, falling back to PATH."""
    try:
        from ruff import find_ruff_bin  # type: ignore[import-untyped]

        candidate: str | None = find_ruff_bin()
        if candidate and os.path.isfile(candidate):
            return candidate
    except Exception:
        pass
    from shutil import which

    return which("ruff")


# --------------------------------------------------------------------------- #
# Anti-cheat: CodeBLEU-style similarity (E12)
# --------------------------------------------------------------------------- #


def _anticheat_flag(learner_code: str, instructor_code: str) -> bool:
    """Flag when learner code is too similar to the instructor's code (E12)."""
    if not learner_code or not instructor_code:
        return False
    sim = _code_similarity(learner_code, instructor_code)
    flagged = sim >= ANTICHEAT_THRESHOLD
    if flagged:
        logger.info("Anti-cheat flag: CodeBLEU similarity %.2f >= %.2f", sim, ANTICHEAT_THRESHOLD)
    return flagged


def _code_similarity(a: str, b: str) -> float:
    """CodeBLEU-style similarity in [0, 1].

    Uses the optional ``codebleu`` package when installed; otherwise falls back
    to a blend of token n-gram BLEU-4 and tree-sitter AST node-type sequence
    similarity, which approximates CodeBLEU's dataflow + n-gram blend.
    """
    if not a or not b:
        return 0.0
    try:
        score = _codebleu_pkg(a, b)
        if score is not None:
            return _clip(score)
    except Exception as exc:
        logger.debug("codebleu package unavailable, using fallback: %s", exc)
    return _fallback_similarity(a, b)


def _codebleu_pkg(candidate: str, reference: str) -> float | None:
    """Use the optional ``codebleu`` package if importable; else return None."""
    try:
        from codebleu import calc_codebleu  # type: ignore[import-not-found]
    except ImportError:
        return None
    result = calc_codebleu(references=[[reference]], hypotheses=[candidate], lang="python")
    if isinstance(result, dict):
        return float(result.get("codebleu", 0.0))
    return float(result)


def _fallback_similarity(a: str, b: str) -> float:
    """Blend token 4-gram BLEU with tree-sitter AST node-type sequence match."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    ngram = _bleu4(tokens_a, tokens_b)
    ast_sim = _ast_similarity(a, b)
    return _clip(0.5 * ngram + 0.5 * ast_sim)


def _tokenize(code: str) -> list[str]:
    """Normalised Python token stream (identifiers, operators, literals lowercased)."""
    return re.findall(
        r"[A-Za-z_]\w*|==|!=|<=|>=|->|[-+*/%=<>!&|^~]|\.|\,|\:|\(|\)|\[|\]|\{|\}|[0-9]+|\"[^\"]*\"|'[^']*'",
        code,
    )


def _bleu4(cand: list[str], ref: list[str]) -> float:
    """Smoothed 4-gram BLEU between two token lists (symmetric max)."""
    if not cand or not ref:
        return 0.0
    weights = [0.25, 0.25, 0.25, 0.25]
    precisions: list[float] = []
    for n in range(1, 5):
        grams_c = _ngrams(cand, n)
        grams_r = _ngrams(ref, n)
        if not grams_c:
            precisions.append(1e-9)
            continue
        matches = sum(min(count, grams_r.get(g, 0)) for g, count in grams_c.items())
        precisions.append(max(matches, 1e-9) / max(len(grams_c), 1))
    log_avg = sum(w * math.log(p) for w, p in zip(weights, precisions, strict=True)) / sum(weights)
    bp = 1.0 if len(cand) >= len(ref) else math.exp(1 - len(ref) / max(len(cand), 1))
    return _clip(bp * math.exp(log_avg))


def _ngrams(tokens: list[str], n: int) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    for i in range(len(tokens) - n + 1):
        g = tuple(tokens[i : i + n])
        counts[g] = counts.get(g, 0) + 1
    return counts


def _ast_similarity(a: str, b: str) -> float:
    """Jaccard similarity over the multiset of tree-sitter node types."""
    types_a = _ast_node_types(a)
    types_b = _ast_node_types(b)
    if not types_a and not types_b:
        return 0.0
    set_a = set(types_a)
    set_b = set(types_b)
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


def _ast_node_types(code: str) -> list[str]:
    """Return the sequence of tree-sitter node types for ``code``."""
    try:
        from tree_sitter import Language, Parser
        from tree_sitter_python import language
    except ImportError:
        return []
    try:
        lang = Language(language())
        parser = Parser(lang)
        tree = parser.parse(code.encode("utf-8"))
    except Exception:
        return []
    types: list[str] = []
    stack: list[Any] = [tree.root_node]
    while stack:
        node = stack.pop()
        types.append(node.type)
        # push children in reverse so traversal is deterministic
        children = node.children
        for child in reversed(children):
            stack.append(child)
    return types


# --------------------------------------------------------------------------- #
# Embeddings (sentence-transformers, token-overlap fallback)
# --------------------------------------------------------------------------- #


_embedder: Any = None
_embedder_failed = False


def _get_embedder() -> Any:
    """Lazy singleton for the sentence-transformers model (mirrors M4)."""
    global _embedder, _embedder_failed
    if _embedder_failed:
        return None
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer

            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            logger.warning("sentence-transformers unavailable, using token-overlap: %s", exc)
            _embedder_failed = True
            return None
    return _embedder


def _embedding_similarity(a: str, b: str) -> float:
    """Cosine similarity between two texts via embeddings (token-overlap fallback)."""
    embedder = _get_embedder()
    if embedder is None:
        return _token_overlap(a, b)
    try:
        import numpy as np

        emb = embedder.encode([a, b], normalize_embeddings=True)
        vec_a = np.asarray(emb[0], dtype=np.float32)
        vec_b = np.asarray(emb[1], dtype=np.float32)
        return _clip(float(np.dot(vec_a, vec_b)))
    except Exception as exc:
        logger.warning("embedding failed, using token-overlap: %s", exc)
        return _token_overlap(a, b)


def _token_overlap(a: str, b: str) -> float:
    """Fallback cosine over bag-of-words (word-level, lowercased)."""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa and not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return inter / union if union else 0.0


# --------------------------------------------------------------------------- #
# LLM-as-a-Judge
# --------------------------------------------------------------------------- #


_JUDGE_DEFAULTS: dict[str, dict[str, Any]] = {
    "judge_code": {"score": 0.0, "explanation": "", "hints": []},
    "judge_conceptual": {"score": 0.0, "explanation": "", "hints": []},
    "judge_debug": {"score": 0.0, "explanation": "", "hints": []},
}


def _llm_judge(
    client: LLMClient,
    kind: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    """Render the judge template for ``kind`` and parse the LLM's JSON verdict."""
    defaults = _JUDGE_DEFAULTS.get(kind, _JUDGE_DEFAULTS["judge_code"])
    try:
        template = _load_template(kind)
        rendered = _render(template, variables)
        rendered += "\n\nRespond with ONLY a JSON object. No markdown fences, no prose."
        raw = client.complete(rendered, system=_SYSTEM)
        parsed = _parse_json(raw)
        return {
            "score": _coerce_float(parsed.get("score", defaults["score"])),
            "explanation": str(parsed.get("explanation", defaults["explanation"])),
            "hints": list(parsed.get("hints", defaults["hints"]) or []),
        }
    except (json.JSONDecodeError, KeyError, TypeError, FileNotFoundError) as exc:
        logger.warning("LLM judge (%s) failed, using defaults: %s", kind, exc)
        return dict(defaults)


# --------------------------------------------------------------------------- #
# Prompt loading + rendering helpers (mirror M7/M8)
# --------------------------------------------------------------------------- #


def _load_template(kind: str) -> str:
    path = _PROMPT_DIR / kind / "template.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


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


# --------------------------------------------------------------------------- #
# Result builder + coercion helpers
# --------------------------------------------------------------------------- #


def _to_result(
    verdict: str,
    score: float,
    explanation: str,
    hints: list[str],
    anti_cheat: bool,
    exercise: dict[str, Any],
) -> dict[str, Any]:
    """Validate against ``EvalResult`` and return the 5-key result dict."""
    score = _clip(score)
    if verdict not in ("pass", "fail", "partial"):
        verdict = "fail"
    ex_id = str(exercise.get("id", "unknown"))
    try:
        result = EvalResult(
            exercise_id=ex_id,
            verdict=verdict,
            score=score,
            explanation=explanation or "(no explanation)",
            hints=list(hints),
            anti_cheat_flag=bool(anti_cheat),
        )
        validated = result.model_dump(mode="json")
        return {
            "verdict": validated["verdict"],
            "score": validated["score"],
            "explanation": validated["explanation"],
            "hints": validated["hints"],
            "anti_cheat_flag": validated["anti_cheat_flag"],
        }
    except ValidationError as exc:
        logger.warning("EvalResult validation failed for %s: %s", ex_id, exc)
        return {
            "verdict": verdict,
            "score": score,
            "explanation": explanation or "(no explanation)",
            "hints": list(hints),
            "anti_cheat_flag": bool(anti_cheat),
        }


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
