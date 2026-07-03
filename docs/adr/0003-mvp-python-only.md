# ADR 0003: MVP Languages - Python Only

- **Status:** Accepted (locked decision #3)
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** Locked Decisions

## Context

Supporting multiple coding languages multiplies the test harness, sandbox config,
and OCR/syntax surface. MVP must stay focused.

## Decision

MVP supports Python only for coding exercises. JS/TS/Java/C++ deferred to Phase 6.
Non-Python content detected in a video is marked as MCQ/conceptual instead (risk E11).

## Consequences

- Positive: smaller surface, faster to MVP
- Negative: loses non-Python tutorial coverage until Phase 6
- Risks: E11 (mitigated by detecting non-Python and downgrading exercise type)
