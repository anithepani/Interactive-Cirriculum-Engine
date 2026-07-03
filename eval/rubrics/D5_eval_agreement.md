# Eval-Engine Agreement (D.5)

Owner: **Aryan**

Measures how often the M9 evaluation engine agrees with a human rubric on the
verdict/score for a held-out set of learner responses.

## Target

- >=85% agreement with human rubric (verdict: pass/fail/partial)
- For partial-credit scores, Pearson r >= 0.7 vs human scores

## Procedure

1. Curate a held-out set of (exercise, learner_response, human_verdict, human_score).
2. Run the M9 eval engine; compare verdict + score.
3. Write `eval/reports/eval-agreement-<date>.json`.
