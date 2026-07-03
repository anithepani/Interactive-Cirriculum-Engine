# Runbook: Handle GPT-4o Outage / Over Budget

Triggers: OpenAI API 5xx, latency spike, or `LLM_TOKEN_BUDGET_PER_CURRICULUM`
exceeded for a tenant (risk E16). The system should degrade automatically per §6.4;
this runbook is for manual confirmation/recovery.

## Automatic degradation (already wired in `libs/ai/llm/`)

When GPT-4o is unavailable or over budget, `LLMClient.complete(tier="high_value")`
falls back to:
- generation -> Llama 3.1 70B (Groq/Together via `LLM_FALLBACK_MODEL`)
- code generation -> Qwen2.5-Coder-32B (`LLM_CODE_MODEL`)

## Manual steps

1. Check OpenAI status page + Sentry for the error rate.
2. Confirm the worker pool is draining (no new `gpt-4o` calls): `flower` -> queue depth.
3. If a tenant is over budget, the pipeline pauses + notifies admin (§6.4). Approve
   a top-up by updating `tenants.token_budget` or wait for the window to reset.
4. When GPT-4o recovers, no action needed - routing reverts automatically.
5. File an incident note in `eval/reports/` if quality dipped during the window.

## Fallback tree (§6.4)

| Trigger | Fallback |
| --- | --- |
| GPT-4o down/over budget | Llama 3.1 70B / Qwen2.5-Coder |
| OCR confidence low | transcript-only exercises; flag "code unclear" (E1) |
| ASR WER high | slide+concept-only mode; allow manual transcript upload (E2) |
| judge0 pool saturated | queue submissions; return "grading pending" + webhook (E18) |
| GPU node down | cloud Whisper API + cloud OCR (higher cost, capped) |
| Tenant budget exceeded | pause pipeline; notify admin; allow top-up |
