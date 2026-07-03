# M14 Code Execution Sandbox

Sandboxed Python execution for coding challenges + debug tasks (MVP language: Python,
locked decision #3). Resource-capped: CPU/mem/time/net (risk E19).

## MVP: judge0

Docker-based, multi-language, fast. Runs in the dev stack (`infra/compose/docker-compose.dev.yml`,
port 2358). Configured via `JUDGE0_*` and `SANDBOX_*` env vars.

## Production: Firecracker microVM

Strongest isolation. nsjail as fallback. No filesystem persistence; CPU/mem/time/net
caps enforced per submission. Tenant-tagged. Lands in Phase 5.

## Interface

```
Input:  learner code + tests + language (Python MVP)
Output:  pass/fail, stdout/stderr, runtime, exit code
```

The M9 evaluation engine (`libs/ai/evaluation/`) consumes the sandbox result +
runs LLM-as-judge for partial credit, style, and anti-cheat (CodeBLEU).

## Anti-cheat (risk E12)

Before returning a verdict, the eval engine runs CodeBLEU/AST-diff similarity vs the
instructor's extracted code. If too similar, the submission is rejected and a fresh
variant is regenerated (UC-13 retry/revisit).

Owner: **Zubair**. Support: Aryan (eval integration).
