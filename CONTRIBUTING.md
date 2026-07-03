# Contributing to the Interactive Curriculum Engine

This document defines the branching strategy, PR rules, and the contract-first development order for the 3-person team. Read it before branching off `main`.

---

## Branching Strategy: Trunk-based GitHub Flow

We use **trunk-based GitHub Flow** with phase release tags. This is lightweight, keeps integration honest, and surfaces contract drift early — suited to a 3-person startup with weekly phase milestones and CI gates.

### Branches

- **`main`** — protected, always deployable. PRs require passing CI + 1 review.
- **`feat/<owner>-<module>-<topic>`** — short-lived feature branches.
  - Example: `feat/aryan-m7-exercise-gen-mcq`
  - The owner prefix makes CODEOWNERS routing and reviews obvious.
- **`fix/`**, **`chore/`**, **`docs/`**, **`refactor/`** — conventional prefixes.
- **`release/v<phase>`** — tagged milestones per the phase plan (§8).
  - e.g. `release/v0-foundations`, `release/v1-ingestion`, `release/v2-segmentation`
  - These are **annotated tags**, not long-lived branches.

> No long-lived `develop` branch. (Optional `develop` only during Phase 0 while contracts finalize, deleted once locked.)

### Lifecycle

1. Branch off the latest `main`: `git checkout -b feat/aryan-m4-segmentation-bertopic main`
2. Commit in small, reviewable chunks. Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(m4): add BERTopic candidate-boundary detection`
   - `fix(api): correct tenant_id propagation in eval router`
   - `docs(adr): record hybrid LLM decision`
3. Push and open a PR against `main`.
4. CI must be green and a reviewer must approve.
5. Squash-merge. Delete the branch.

### Phase boundaries (§8)

At the end of each development phase, the integration lead (Zubair) tags `release/v<n>-<name>`. The golden-set eval suite (`make eval`) must pass the phase acceptance criteria before tagging.

---

## Contract-First Development (§5.3)

The integration seam between AI (Aryan/Ahmed, producers) and the application (Zubair, consumer) is **`libs/contracts/`**. It holds Pydantic models for every canonical JSON shape defined in the master plan's §5.3.1:

- transcript segment
- visual extraction item
- concept
- segment / topic
- exercise (union schema: mcq | coding | debug | conceptual)
- eval result

### Hard rules

1. **Define the contract before coding the module.** Aryan publishes the I/O schema in `libs/contracts/`; Zubair consumes it. No AI package may emit a shape not modeled here.
2. **Any change to `libs/contracts/` requires sign-off from both Aryan and Zubair.** Both are CODEOWNERS of that path.
3. **Backend/AI schema drift is a CI failure.** Contract tests in `tests/contract/` validate live endpoints against `libs/contracts/`.
4. **DB schema changes ship an Alembic migration + an RLS test.** Zubair owns `db/` and `docs/data-model/`.
5. **AI-package PRs that change behavior must include a golden-set eval delta** in `eval/reports/` (Appendix D rubrics).

### Development order per module

```
1. Aryan defines request/response in libs/contracts/   (producer)
2. Zubair stubs the API/router consuming it            (consumer)
3. Aryan implements the AI module emitting the contract
4. Zubair wires the worker task + persistence
5. Both sign the contract test in tests/contract/
```

---

## Pull Request Rules

- [ ] Branch name follows `feat|fix|chore|docs|refactor/<owner>-<module>-<topic>`
- [ ] Conventional Commits message
- [ ] CI is green (ruff, mypy, eslint, tsc, pytest, vitest)
- [ ] At least one reviewer approves (CODEOWNERS auto-requests the right one)
- [ ] If touching `libs/contracts/` — both Aryan AND Zubair approved
- [ ] If touching `db/migrations/` — migration is reversible + RLS test added
- [ ] If AI behavior changed — golden-set eval delta attached
- [ ] No secrets in diff (detect-secrets pre-commit + CI scan)
- [ ] `make lint`, `make typecheck`, `make test` pass locally

---

## Local Quality Gates

```bash
make lint         # ruff + eslint
make typecheck    # mypy + tsc
make test         # unit tests (excludes integration/e2e/gpu/golden)
make test-integration   # needs live compose stack
make eval         # golden-set regression (Appendix D)
```

Pre-commit hooks (`.pre-commit-config.yaml`) run on every commit: trailing whitespace, ruff, mypy, codespell, detect-secrets. Install once via `make bootstrap`.

---

## Multi-Tenancy Discipline

Every record carries `tenant_id`. Postgres Row-Level Security enforces isolation. When adding a table or query:

- Include `tenant_id` column (UUID, NOT NULL, indexed).
- Add an RLS policy in the migration.
- Ensure the app sets `app.tenant_id` in the session before any query.
- Tenant-scoped object storage uses prefix `tenants/<tenant_id>/...`.
- judge0 submissions are tagged with the tenant.

Cross-tenant data leakage is a P0 security bug — see `docs/runbooks/` and risk E25 in the master plan.

---

## Code Ownership (`.github/CODEOWNERS`)

| Path | Owners |
| --- | --- |
| `libs/contracts/` | Aryan, Zubair (both must approve) |
| `libs/ai/transcript/`, `segmentation/`, `concept_graph/`, `checkpoints/`, `exercise_gen/`, `test_gen/`, `evaluation/`, `adaptive/` | Aryan |
| `libs/ai/vision/`, `libs/ai/ingestion/` (vision parts) | Ahmed |
| `libs/ai/llm/`, `prompt-library/` | Aryan |
| `apps/api/`, `apps/worker/`, `apps/web/`, `db/`, `infra/`, `.github/` | Zubair |
| `eval/` | Aryan (rubrics), Zubair (system metrics) |
| `docs/research/` | per-domain owner |
