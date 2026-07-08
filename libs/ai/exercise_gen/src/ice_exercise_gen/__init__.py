"""M7 Exercise Generation Engine.

Input: checkpoints (M6) + segments (M4) + concepts (M5) + instructor code (M3).
Output: exercises of 4 types - MCQ (with distractors), coding challenge
(prompt + starter + hidden tests + reference solution), debugging task
(buggy snippet + tests), conceptual question (rubric + reference answer).

Tech: GPT-4o primary generator (structured output via prompt + JSON parsing +
Pydantic validation); Qwen2.5-Coder-32B / DeepSeek-Coder-V2 for code-heavy
generation & fallback; few-shot + concept-conditioned prompts; StarCoder2 /
CodeT5 embeddings for similarity to detect copying instructor's example
(forces "new context").

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

from ice_exercise_gen.generator import generate_exercises

__all__ = ["generate_exercises"]
__version__ = "0.1.0"
