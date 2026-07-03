# ADR 0006: Trunk-Based GitHub Flow

- **Status:** Accepted
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** §8 (phases)

## Context

A 3-person team with weekly phase milestones needs a branching model that surfaces
integration problems early and keeps `main` always deployable.

## Decision

Trunk-based GitHub Flow with phase release tags (`release/v<n>-<name>`). Short-lived
`feat/<owner>-<module>-<topic>` branches; squash-merge to `main`. No long-lived
`develop`. See `CONTRIBUTING.md`.

## Consequences

- Positive: contract drift caught in days, not weeks; CI is the gate
- Negative: requires discipline + fast CI
- Risks: none material
