# Shared LLM Client (Hybrid strategy, ADR 0001)

Routes between GPT-4o (high-value) and Llama 3.1 70B / Qwen2.5-Coder (bulk/fallback)
per task tier. Enforces per-curriculum token budgets (cost control, E16), caches
responses, and provides structured-output helpers (function calling / JSON schema).

**Owner:** Aryan. Consumed by all `libs/ai/*` generation + evaluation packages.
