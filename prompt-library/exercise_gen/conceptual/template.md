You are an expert programming instructor designing a **conceptual question** that
tests deep understanding of **{{ concept }}** (not syntax recall).

## Concept
- {{ concept }}: {{ concept_description }}
- Target difficulty (1-5): {{ difficulty }}

## Lesson context
{{ segment_summary }}

## Requirements
1. Write a `prompt` — an open-ended question requiring the learner to **explain**
   or **reason about** `{{ concept }}` (not write code).
2. Write a `reference_answer` — a concise model answer.
3. Write a `rubric` — at least 2 grading rubric items the LLM-as-judge will use
   (M9).  Each item should describe a key point the answer must cover.
4. Set `min_similarity` (0.0–1.0) — the embedding-similarity threshold above
   which the learner's answer auto-passes without LLM grading.
5. Set `confidence` (0.0–1.0).

Return strict JSON conforming to the output schema.
