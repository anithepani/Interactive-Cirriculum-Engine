# ADR 0001: Hybrid LLM Strategy

- **Status:** Accepted (locked decision #1)
- **Date:** 2026-07
- **Deciders:** Aryan, Zubair, Ahmed
- **Master plan ref:** §6.1, Locked Decisions

## Context

We need an LLM for high-value generation (exercises, tests, grading), bulk tasks
(summaries, titles), and a sovereignty/fallback path. Pure GPT-4o is expensive at
scale (risk E16) and has no sovereignty; pure open-source lags on structured
output quality.

## Decision

**Hybrid.** GPT-4o for high-value generation, grading, and structured reasoning;
Llama 3.1 70B / Qwen2.5-Coder-32B for bulk tasks, fallback, and the sovereignty path.
Routing lives in `libs/ai/llm/`.

## Consequences

- Positive: cost control (token budgets per curriculum), sovereignty path, clear degradation (§6.4)
- Negative: two model surfaces to maintain; `ice-llm` must abstract routing
- Risks: E16 cost spikes (mitigated by budgets + caching), E7 hallucination (mitigated by self-consistency)
