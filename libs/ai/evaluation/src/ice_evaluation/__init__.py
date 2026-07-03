"""M9 Answer Evaluation & Feedback Engine.

Input: learner response + exercise + (for code) test results.
Output: verdict, score, explanation, hints, code-quality notes, anti-cheat flag.

Tech:
- MCQ -> exact match + distractor analytics
- code -> judge0 tests + static analysis (ruff for Python MVP) + LLM-as-a-Judge
  with rubric for partial credit & style + CodeBLEU for similarity (anti-cheat)
- conceptual -> LLM judge vs reference answer + embedding similarity threshold

Papers [MUST]: "LLM-as-a-Judge" (Zheng 2023).
Papers [OPT]: CodeBLEU.

Edge case E12 (cheating - copies instructor's code): CodeBLEU/AST diff vs
instructor's extracted code; if too similar, reject + regenerate new variant.
Edge case E13 (guessing MCQs): "explain your choice" step; track response time.

Acceptance (Phase 3): >=85% agreement with human rubric on held-out set.

Lead: Aryan. Support: Zubair (sandbox integration).
"""
from __future__ import annotations

from ice_contracts import EvalResult, Exercise


def evaluate(exercise: Exercise, response: dict, sandbox_result: dict | None = None) -> EvalResult:
    """Return verdict/score/explanation/hints/anti_cheat_flag (session-time, <2s p95)."""
    raise NotImplementedError("Phase 3 deliverable")
