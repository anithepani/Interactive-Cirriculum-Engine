# Architecture Decision Records

ADRs record significant technical decisions and their rationale. Each file is
one ADR following the [Nygard format](https://adr.github.io/).

- [0001-hybrid-llm-strategy.md](0001-hybrid-llm-strategy.md) — GPT-4o + Llama/Qwen fallback (locked decision #1)
- [0002-code-sandbox-judge0-firecracker.md](0002-code-sandbox-judge0-firecracker.md) — judge0 MVP, Firecracker prod (locked #2)
- [0003-mvp-python-only.md](0003-mvp-python-only.md) — Python for coding exercises, JS/TS deferred (locked #3)
- [0004-monorepo-uv-pnpm.md](0004-monorepo-uv-pnpm.md) — polyglot monorepo with uv + pnpm workspaces
- [0005-contract-first-development.md](0005-contract-first-development.md) — `libs/contracts/` as the integration seam
- [0006-trunk-based-github-flow.md](0006-trunk-based-github-flow.md) — branching strategy
- [0007-postgres-rls-multi-tenancy.md](0007-postgres-rls-multi-tenancy.md) — RLS keyed on `app.tenant_id` (locked #5)
- [0008-async-pipeline-celery.md](0008-async-pipeline-celery.md) — heavy work off the request path (risk E17)

Template: [0000-template.md](0000-template.md)
