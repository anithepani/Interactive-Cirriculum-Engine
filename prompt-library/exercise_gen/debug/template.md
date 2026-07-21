You are an expert programming instructor designing a **debugging exercise** that
tests understanding of **{{ concept }}**.

## Concept
- {{ concept }}: {{ concept_description }}
- Target difficulty (1-5): {{ difficulty }}

## Instructor's example (for context only — DO NOT reuse this code verbatim)
The learner already saw this from the instructor:

```python
{{ instructor_code }}
```

## Lesson context (GROUND YOUR QUESTION IN THIS)
Base the exercise **strictly** on the following excerpt from the video so the
bug is one a learner of *this* lesson would realistically encounter.

Segment: {{ segment_title }}
Excerpt:
{{ segment_text }}

Summary: {{ segment_summary }}

## Requirements
1. Write `buggy_code` — a short Python snippet (different from the instructor's
   example) containing a **subtle bug** related to `{{ concept }}`, using the
   same domain/terminology as the excerpt above.
2. Write at least 1 hidden `tests` (as assert statements or function calls)
   that the **fixed** code must pass.  The buggy code must fail at least one.
3. Write `fixed_code` — the **corrected** version of `buggy_code` that passes
   ALL of the `tests`. It must keep the same function/variable names so the
   tests apply unchanged; only the bug is fixed.
4. Write a `prompt` that frames the task for the learner (e.g. "The following
   code has a bug related to {{ concept }}. Find and fix it.").
5. Write `bug_explanation` — the ground-truth explanation of the bug (the
   learner must also submit an explanation, which is LLM-graded).
6. Set `confidence` (0.0–1.0).

Return strict JSON conforming to the output schema.
