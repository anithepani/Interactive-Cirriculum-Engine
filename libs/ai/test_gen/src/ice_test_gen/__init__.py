"""M8 Test Generation & Validation.

Input: coding challenge prompt + reference solution. Output: validated test
cases (visible + hidden) + verified solvability.

Tech: LLM generates N candidate tests + reference solution; mutation testing
to ensure tests catch bugs; CodeT self-consistency (generate multiple
solutions, keep tests passing on majority); execute in sandbox before publish.

Papers [MUST]: "CodeT: Code Generation with Generated Tests" (Chen 2022).
Papers [OPT]: "Self-Debugging" (Chen 2023).

Edge case E14 (AI generates unsolvable challenge): validate every challenge by
solving with a solver LLM + executing tests before exposing; if no solution
passes, regenerate.
Edge case E15 (AI-generated tests wrong): mutation testing on tests;
cross-validate vs reference solution; dedupe equivalent tests.

Acceptance (Phase 3): exercises only become publishable once validation_passed=True.

Lead: Aryan. Support: Zubair (sandbox).
"""
from __future__ import annotations

from ice_contracts import Exercise


def validate_exercise(exercise: Exercise) -> Exercise:
    """Run mutation testing + sandbox execution; return exercise with validation_passed set."""
    raise NotImplementedError("Phase 3 deliverable")
