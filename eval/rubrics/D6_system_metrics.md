# System Metrics (D.6)

Owner: **Zubair**

System-level (non-AI) metrics: latency, cost, reliability, multi-tenant isolation.

## Targets (master plan §8 acceptance)

| Metric | Target |
| --- | --- |
| Eval latency p95 (session-time) | < 2s |
| Pipeline cost per curriculum | bounded by `LLM_TOKEN_BUDGET_PER_CURRICULUM` |
| Pipeline reliability | <2% of curricula end in `failed` after retries |
| Cross-tenant data leakage (E25) | 0 (RLS audit; enforced by `tests/integration/test_rls.py`) |
| Sandbox security (E19) | 0 RCE escapes (judge0/Firecracker caps enforced) |
| API uptime (staging) | >=99% over a release window |

## Procedure

1. `scripts/eval-golden.py` instruments latency + token spend per pipeline run.
2. `tests/integration/test_rls.py` verifies cross-tenant queries return no rows.
3. Prometheus + Grafana (`infra/compose/`) scrape `/metrics` continuously.
4. Write `eval/reports/system-metrics-<date>.json`.
