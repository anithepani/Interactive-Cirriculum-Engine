"""M7 Exercise Generation Engine.

Input: segment + concept + extracted instructor code + difficulty + language
(Python MVP). Output: exercises of 4 types - MCQ (with distractors), coding
challenge (prompt + starter + hidden tests + reference solution), debugging
task (buggy snippet + tests), conceptual question (rubric + reference answer).

Tech: GPT-4o primary generator (structured output via function calling / JSON
schema); Qwen2.5-Coder-32B / DeepSeek-Coder-V2 for code-heavy generation &
fallback; few-shot + concept-conditioned prompts; StarCoder2 / CodeT5
embeddings for similarity to detect copying instructor's example (forces
"new context").

Key design: exercises test TRANSFER, not recall - the generated coding
challenge uses a different context than the instructor's example.

Papers [MUST]: APPS/HumanEval/MBPP for calibration.
Papers [OPT]: "Learning to Generate Questions by Learning to Answer"; UniLM;
Codex; AlphaCode.

Acceptance (Phase 3): >=90% of generated coding challenges pass automated
validation (solvable by reference solution).

Lead: Aryan. Support: Ahmed (code-context from OCR).
"""
from __future__ import annotations

from ice_contracts import Checkpoint, Exercise


def generate_exercises(checkpoints: list[Checkpoint], instructor_code: list[str]) -> list[Exercise]:
    """Generate MCQ/coding/debug/conceptual per checkpoint."""
    raise NotImplementedError("Phase 3 deliverable - see prompt-library/exercise_gen/")
