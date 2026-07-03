# Eval Suite (Appendix D)

Proves that the AI-generated curriculum is actually good. Runs in CI
(`eval-regression.yml`) on every release tag and on PRs that touch `libs/ai/**`
or `prompt-library/**`, failing on regression.

## Structure

- `golden_set/` — 5 curated tutorial videos (D.1) + their expected outputs
- `rubrics/` — the rubric definitions (D.2-D.6)
- `benchmarks/` — HumanEval / MBPP / APPS calibration harness + mutation-testing runner
- `reports/` — generated eval reports per release (committed; CI uploads artifacts)

## Acceptance gates (master plan §8)

| Gate | Rubric | Target |
| --- | --- | --- |
| Checkpoint placement precision | D.2 | >=80% land on real topic boundaries |
| Coding challenge solvability | D.3 | >=90% pass automated validation |
| Eval-engine agreement | D.5 | >=85% agreement with human rubric |
| Eval latency | D.6 | p95 < 2s (session-time) |

Owners: **Aryan** (rubrics D.2-D.5), **Zubair** (D.6 system metrics).
