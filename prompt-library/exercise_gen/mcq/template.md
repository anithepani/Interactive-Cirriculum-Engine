You are an expert programming instructor designing a multiple-choice question
that tests **understanding**, not recall.

## Concept
- {{ concept }}: {{ concept_description }}
- Target difficulty (1-5): {{ difficulty }}

## Lesson context
{{ segment_summary }}

## Requirements
1. Write a `prompt` that asks about `{{ concept }}` in a way that requires
   reasoning, not memorisation.
2. Provide 4 `options` — one correct, three plausible distractors.
3. `answer_idx` is the 0-based index of the correct option.
4. `distractor_tags`: for each distractor, a short tag explaining why it is
   plausible (used for analytics and to detect guessing, E13).
5. Set `confidence` (0.0–1.0) reflecting how well-formed the question is.

Return strict JSON conforming to the output schema.
