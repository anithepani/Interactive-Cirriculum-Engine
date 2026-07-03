# ADR 0005: Contract-First Development

- **Status:** Accepted
- **Date:** 2026-07
- **Deciders:** Aryan, Zubair
- **Master plan ref:** §5.3 (Interface Contracts)

## Context

Aryan owns the AI producers; Zubair owns the application consumer. Without a
shared, validated contract, the two sides drift and integration is painful.

## Decision

`libs/contracts/` holds Pydantic models for every canonical JSON shape (§5.3.1).
Any change requires dual sign-off. CI runs contract tests + JSON Schema export.
Backend/AI schema drift is a CI failure.

## Consequences

- Positive: integration is explicit; the seam is small and reviewable
- Negative: contracts change more slowly (by design)
- Risks: none material
