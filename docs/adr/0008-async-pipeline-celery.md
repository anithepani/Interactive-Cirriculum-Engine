# ADR 0008: Async Pipeline via Celery

- **Status:** Accepted
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** §6.2, risk E17

## Context

The generation pipeline (ingest -> ASR -> OCR -> segment -> gen -> validate) is
heavy and slow. Interactive UX requires session-time calls to stay fast (<2s p95, E17).

## Decision

The heavy pipeline runs async in Celery (`apps/worker`). The full curriculum is
pre-generated before the learner starts a session. Session-time API calls are limited
to fast evaluation. Failures retry with backoff; per-curriculum token budgets enforced.

## Consequences

- Positive: fast session UX; cost control (token budgets); parallelizable stages
- Negative: extra infra (Redis + worker pool); status polling / WebSocket for progress
- Risks: E17 (mitigated by pre-generation), E16 (mitigated by budgets + caching)
