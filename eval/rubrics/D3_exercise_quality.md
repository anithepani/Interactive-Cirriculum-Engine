# Exercise Quality Rubric (D.3) - human-rated

Owner: **Aryan**

Human-rated quality of generated exercises. Sampled (not exhaustive) —
N=20 exercises per golden video per release.

## Dimensions (each 1-5 Likert)

| Dimension | Question |
| --- | --- |
| Correctness | Is the exercise solvable? Does the reference solution pass all tests? |
| Transfer | Does it test the concept in a NEW context (not the instructor's example)? |
| Clarity | Is the prompt unambiguous to a learner? |
| Difficulty calibration | Does the perceived difficulty match the target 1-5? |
| Test adequacy | Do the hidden tests catch plausible wrong answers (mutation-tested)? |
| Anti-cheat | Would copying the instructor's code fail the tests (CodeBLEU)? |

## Targets

- >=90% of coding challenges pass automated validation (solvable by reference solution)
- Mean human rating >=3.5 across all dimensions
- <5% of exercises flagged "unsolvable" or "ambiguous" by reviewers

## Procedure

1. Sample 20 exercises per golden video.
2. Two reviewers rate each (blind). Resolve disagreements >2 points.
3. Write `eval/reports/exercise-quality-<date>.json`.
