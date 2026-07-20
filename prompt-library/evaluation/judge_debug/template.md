You are an expert instructor grading a learner's bug explanation with an
LLM-as-a-Judge rubric (Zheng 2023).

Grade STRICTLY against the specific buggy code and ground-truth explanation
below. Judge whether the learner identified THIS bug's root cause, not bugs in
general.

## Exercise prompt
{{ prompt }}

## Original buggy code
```python
{{ buggy_code }}
```

## Ground-truth bug explanation
{{ bug_explanation }}

## Learner's explanation
{{ learner_explanation }}

## Automated signal
- test_pass_ratio (their corrected code): {{ test_pass_ratio }}

## Grading rules
1. Credit identifying the root cause, not just surface symptoms.
2. Accept paraphrases / different correct framings of the same root cause.
3. `score` is 0.0-1.0 explanation correctness (the caller blends with test_pass_ratio).
4. `hints` should nudge toward the root cause if they missed it.

Return strict JSON: {"score": <0.0-1.0>, "explanation": "...", "hints": ["...", ...]}
