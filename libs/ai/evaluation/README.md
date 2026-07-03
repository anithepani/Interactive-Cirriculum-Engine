# M9 - Answer Evaluation & Feedback Engine

- MCQ -> exact match + distractor analytics
- code -> judge0 tests + ruff static analysis + LLM-as-a-Judge (partial credit & style) + CodeBLEU (anti-cheat)
- conceptual -> LLM judge vs reference answer + embedding similarity threshold

Returns verdict, score, explanation, hints, anti-cheat flag. Session-time; target <2s p95.

**Lead:** Aryan · **Support:** Zubair (sandbox integration)

Papers [MUST]: "LLM-as-a-Judge" (Zheng 2023).
Acceptance: >=85% agreement with human rubric.
