# ADR 0002: Code Sandbox - judge0 (MVP) -> Firecracker (prod)

- **Status:** Accepted (locked decision #2)
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** Locked Decisions, §6.2, risk E19

## Context

Coding challenges need sandboxed Python execution with strict resource caps and
no RCE escape (risk E19). We need speed now and strongest isolation in prod.

## Decision

judge0 (Docker-based, multi-language) for MVP; Firecracker microVM for prod; nsjail
as fallback. CPU/mem/time/net caps per submission; no filesystem persistence;
tenant-tagged.

## Consequences

- Positive: fast path now, hard isolation later; both already documented
- Negative: one migration (judge0 -> Firecracker) in Phase 5
- Risks: E19 (mitigated by caps + microVM)
