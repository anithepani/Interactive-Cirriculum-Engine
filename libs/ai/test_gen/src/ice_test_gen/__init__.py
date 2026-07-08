"""M8 Test Generation & Validation.

Input: a coding exercise (with ``reference_solution`` + optional ``starter``).
Output: validated visible + hidden test cases + verified solvability.

Tech: LLM generates candidate tests; CodeT self-consistency (Chen 2022) generates
multiple reference solutions and keeps tests passing on the majority; mutation
testing injects common bugs (off-by-one, missing edge cases, wrong operator) and
verifies the tests catch them; pre-validation runs in a local subprocess sandbox
(pluggable for judge0). Retries up to 3 times on validation failure.

Papers [MUST]: "CodeT: Code Generation with Generated Tests" (Chen 2022).
Papers [OPT]: "Self-Debugging" (Chen 2023).

Edge case E14 (AI generates unsolvable challenge): every challenge is validated
by running tests against the reference solution + CodeT consensus before publish.
Edge case E15 (AI-generated tests wrong): mutation testing on tests; cross-
validate vs multiple reference solutions; reject tests that fail on the reference.

Acceptance (Phase 3): exercises only become publishable once
``validation_passed=True``.

Lead: Aryan. Support: Zubair (sandbox).
"""

from __future__ import annotations

from ice_test_gen.generator import generate_tests

__all__ = ["generate_tests"]
__version__ = "0.1.0"
