# Golden Test Set (D.1)

Five curated tutorial videos used to benchmark every release. Each entry below is
a directory containing the source reference (YouTube URL or local clip under
`data/samples/`), an expected transcript excerpt, expected concept list, and
expected checkpoint plan.

## Acceptance

A release passes when:
- D.2: >=80% of generated checkpoints land on real topic boundaries (here)
- D.3: >=90% of generated coding challenges pass automated validation
- D.5: >=85% eval-engine agreement with the human rubric

## Videos

| ID | Title | Source | Language | Concepts |
| --- | --- | --- | --- | --- |
| G1 | Python Dictionaries | youtube:XXXXX | en | dicts, get, keys, values, items |
| G2 | React useState Hook | youtube:XXXXX | en | hooks, state, re-render |
| G3 | SQL JOINs | youtube:XXXXX | en | inner/outer join, on clause |
| G4 | Git Branching | youtube:XXXXX | en | branch, merge, conflict |
| G5 | Recursion (factorial) | youtube:XXXXX | en | base case, call stack |

> Replace `XXXXX` with the real video IDs once the golden set is curated (Phase 5).
> Keep the raw clips out of git (use `data/samples/` + object storage).
