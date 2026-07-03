# Onboarding

Welcome to the Interactive Curriculum Engine team. This gets you from a fresh clone
to running the dev stack and your first commit.

## 1. Read first

- [`README.md`](../../README.md) — project overview, tech stack, layout
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — branching, PR rules, contract-first workflow
- [Architecture](../architecture/README.md) — the §4.1 diagram + module map
- Your domain's reading list in [`docs/research/`](../research/README.md)

## 2. Get access

- GitHub repo (ask Zubair)
- `.env` secrets you need (by owner):
  - Aryan: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`
  - Zubair: OAuth secrets, `JWT_SECRET`, `S3_*`, `JUDGE0_*`
  - Ahmed: GPU node SSH access (for self-hosted Whisper/PaddleOCR)
- Sentry + Grafana (Zubair)

## 3. Local setup

```bash
git clone <repo> && cd interactive-curriculum-engine
cp .env.example .env       # fill in your secrets
make bootstrap             # uv sync + pnpm install + pre-commit hooks
make dev                   # docker compose up (postgres, redis, minio, judge0, api, worker, web)
make migrate               # alembic upgrade head (creates the 15 tables + RLS)
make seed                  # sample tenant/user/curriculum
make run-pipeline          # Phase-0 smoke test on a sample video
```

Endpoints after `make dev`:
- API docs: http://localhost:8000/docs
- Web: http://localhost:3000
- Flower (Celery): `uv run celery -A ice_worker.celery_app flower` -> http://localhost:5555
- Grafana: http://localhost:3001 (admin/grafana_dev)
- MinIO console: http://localhost:9001 (ice_minio / ice_minio_secret)

## 4. Quality gates before you commit

```bash
make lint         # ruff + eslint
make typecheck    # mypy + tsc
make test         # unit tests
```

Pre-commit hooks run automatically. CI runs the same gates + integration/contract/RLS checks.

## 5. Branch off

```bash
git checkout -b feat/<owner>-<module>-<topic> main
# e.g. feat/aryan-m4-segmentation-bertopic
```

Follow the contract-first order in [`CONTRIBUTING.md`](../../CONTRIBUTING.md):
define the contract in `libs/contracts/` -> stub the consumer -> implement -> sign.

## 6. Phase 0 acceptance (end of Week 1)

Each member should be able to:
- Run `make dev` + `make migrate` cleanly
- Run a demo notebook/script of their core model on a sample tutorial:
  - Aryan: Whisper transcript on a sample video
  - Ahmed: PaddleOCR on sample frames
  - Zubair: API `/health` + a seeded curriculum via `/docs`
- The §5.3 contracts are signed off (dual Aryan+Zubair on `libs/contracts/`)
