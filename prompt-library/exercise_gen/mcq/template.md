You are an expert programming instructor designing a multiple-choice question
that tests **understanding**, not recall.

## Concept
- {{ concept }}: {{ concept_description }}
- Target difficulty (1-5): {{ difficulty }}

## Lesson context (GROUND YOUR QUESTION IN THIS)
Base the question **strictly** on the following excerpt from the video. Do NOT
ask generic textbook trivia; the question must reflect what was actually taught
in this segment.

Segment: {{ segment_title }}
Excerpt:
{{ segment_text }}

Summary: {{ segment_summary }}

## Requirements
1. Write a `prompt` that asks about `{{ concept }}` **as presented in the excerpt
   above**, in a way that requires reasoning, not memorisation.
2. Provide 4 `options` — one correct, three plausible distractors.
3. `answer_idx` is the 0-based index of the correct option.
4. `distractor_tags`: for each distractor, a short tag explaining why it is
   plausible (used for analytics and to detect guessing, E13).
5. Set `confidence` (0.0–1.0) reflecting how well-formed the question is.

Return strict JSON conforming to the output schema.
