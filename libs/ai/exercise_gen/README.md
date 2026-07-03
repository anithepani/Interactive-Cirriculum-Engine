# M7 - Exercise Generation Engine

Generates 4 exercise types per checkpoint: MCQ (with distractors), coding challenge
(prompt + starter + hidden tests + reference solution), debugging task (buggy snippet
+ tests), conceptual question (rubric + reference answer).

GPT-4o primary (structured output via function calling); Qwen2.5-Coder-32B for
code-heavy + fallback. Few-shot + concept-conditioned prompts from `prompt-library/exercise_gen/`.

**Key design:** exercises test TRANSFER, not recall - the coding challenge uses a
different context than the instructor's example.

**Lead:** Aryan · **Support:** Ahmed (code-context from OCR)

Acceptance: >=90% of coding challenges pass automated validation.
