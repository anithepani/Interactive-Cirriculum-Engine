# ADR 0004: Polyglot Monorepo with uv + pnpm Workspaces

- **Status:** Accepted
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** §4.1 (shared contracts), §8.1 ("set up monorepo")

## Context

The AI modules (Aryan/Ahmed) and the application (Zubair) share canonical JSON
contracts (§5.3). A split-repo approach forces contract drift and slow iteration.
A monorepo keeps the contracts in one importable package and lets CI catch drift
on every PR.

## Decision

Adopt a **polyglot monorepo**: `uv` workspaces for Python (apps + libs), `pnpm`
workspaces for the Next.js frontend. `libs/contracts/` is the single source of
truth imported by both sides.

## Consequences

- Positive: contract-first development, atomic cross-cutting changes, shared CI
- Negative: larger repo, tooling complexity; mitigated by path-filtered CI jobs
- Risks: none material
