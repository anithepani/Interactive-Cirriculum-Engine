<!--
Thanks for contributing! Fill in the sections below.
Contract-first rules live in CONTRIBUTING.md.
-->

## Summary

<!-- 1-2 sentences: what does this PR do and why? -->

## Type of change

- [ ] `feat` new feature
- [ ] `fix` bug fix
- [ ] `refactor` no behavior change
- [ ] `docs` documentation only
- [ ] `chore` infra/CI/build
- [ ] `test` test-only

## Linked module / phase

<!-- e.g. M7 Exercise Generation, Phase 3 -->

## Checklist

- [ ] Branch follows `feat|fix|chore|docs|refactor/<owner>-<module>-<topic>`
- [ ] Conventional Commit messages used
- [ ] `make lint` passes (ruff + eslint)
- [ ] `make typecheck` passes (mypy + tsc)
- [ ] `make test` passes (unit tests)
- [ ] No secrets in diff (detect-secrets passed)

## Contract impact (if touching `libs/contracts/`)

- [ ] This PR changes a canonical JSON schema (§5.3)
- [ ] Both **@aryan** (producer) and **@zubair** (consumer) have approved
- [ ] `tests/contract/` updated
- [ ] Downstream consumers notified

## Database impact (if touching `db/migrations/`)

- [ ] Alembic migration added (reversible: `downgrade` works)
- [ ] Row-Level Security policy added/updated (multi-tenant)
- [ ] `tenant_id` column + index present on any new table

## AI behavior change (if touching `libs/ai/*` or `prompt-library/`)

- [ ] Golden-set eval delta attached in `eval/reports/`
- [ ] Acceptance gate still met (e.g. ≥90% solvable coding challenges, ≥85% eval-engine agreement)
- [ ] Prompt `manifest.yaml` version bumped (if prompt changed)

## Test plan

<!-- How did you verify this? Steps a reviewer can reproduce. -->
