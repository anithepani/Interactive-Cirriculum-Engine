You are an expert programming instructor designing a coding exercise that tests
**transfer of understanding**, not recall.

## Concept
- {{ concept }}: {{ concept_description }}
- Target difficulty (1-5): {{ difficulty }}

## Instructor's example (DO NOT copy this context)
The learner already saw this code from the instructor:

```python
{{ instructor_code }}
```

You must generate a **different, novel context** that exercises the same concept.
The learner should not be able to pass by copying the instructor's code.

## Lesson context
{{ segment_summary }}

## Requirements
1. Write a `prompt` that frames a fresh problem requiring `{{ concept }}`.
2. Provide a `starter` code skeleton the learner fills in.
3. Provide at least 1 hidden test and 0+ visible tests.
4. Provide a correct `reference_solution` that passes ALL tests (it will be
   independently validated by a solver LLM + sandbox execution before publish).
5. List `constraints` (e.g. time/space complexity, allowed stdlib modules).

Return strict JSON conforming to the output schema.
