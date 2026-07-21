# Interactive Curriculum Engine

> Convert any technical tutorial video into a structured, interactive, adaptive learning session — automatically generating checkpoints, MCQs, coding challenges, debugging tasks, and conceptual questions that test **transfer of understanding, not recall**.

**Domain:** EdTech · Video Understanding · Multimodal AI · Curriculum Generation

This repository is the foundational blueprint for a 3-person project that turns passive tutorial watching into active practice, escaping "tutorial hell" at a fraction of the cost of manual curriculum creation.

---

## Status

`v0.1.0` — Phase 0 (R&D Spike & Foundations). Decisions locked; contracts being ratified.

## Team & Ownership

| Owner | Domain | Primary modules |
| --- | --- | --- |
| **Zubair** (Full-stack / System Glue) | Product surface & reliability | M1 ingestion, M11 progress, M12 frontend, M13 backend, M14 sandbox, M15 monitoring, infra/CI-CD |
| **Aryan** (AI Lead) | Intelligence & correctness | M2 transcript, M4 segmentation, M5 concept-graph, M6 checkpoints, M7 exercise-gen, M8 test-gen, M9 evaluation, M10 adaptive, prompt library, eval suite |
| **Muhammad Ahmed** (CV/Hardware) | Perception & multimodal fusion | M3 visual extraction, GPU/hardware acceleration, (stretch) ESP32 companion |

## Tech Stack (locked)

- **Backend:** FastAPI (Python 3.11, async)
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + Monaco + Plyr
- **DB:** PostgreSQL 16 + pgvector (RLS by tenant)
- **Cache/Queue:** Redis 7 + Celery
- **Object storage:** MinIO / S3 (tenant-scoped prefixes)
- **Code sandbox:** judge0 (MVP) → Firecracker microVM (prod)
- **ASR:** Whisper large-v3 via faster-whisper + pyannote + silero-vad
- **Vision:** PaddleOCR 2.7 + TrOCR + OpenCV + PySceneDetect + CLIP + Real-ESRGAN
- **LLMs:** GPT-4o (high-value) + Llama 3.1 70B / Qwen2.5-Coder (bulk/fallback) — Hybrid
- **Infra:** Docker Compose (dev) → Kubernetes (prod), GitHub Actions, Terraform (Phase 5)
- **Monitoring:** Prometheus + Grafana + Sentry

## Repository Layout

```
apps/        Deployable runtime services (web, api, worker)
libs/        Reusable packages: contracts (the integration seam), shared, ai/* (M1-M11)
sandbox/     M14 code-execution sandbox (judge0 -> Firecracker)
prompt-library/  Versioned prompts (drift alerts + regression per release)
db/          Alembic migrations (15 tenant-scoped tables + RLS + pgvector)
eval/        Golden test set + rubrics (Appendix D) + benchmarks
data/        Sample inputs + fixtures (large datasets live in object storage)
tests/       Cross-cutting integration / e2e / contract tests
infra/       Dockerfiles, docker-compose.dev.yml, k8s/, terraform/
docs/        Architecture, ADRs, OpenAPI, ER, contracts, research, runbooks
scripts/     Cross-platform dev + ops utilities
.github/     CI/CD workflows, CODEOWNERS, PR/issue templates
```

## Quick Start

```bash
# 1. Bootstrap (installs py + node deps, pre-commit hooks)
make bootstrap

# 2. Configure environment
cp .env.example .env
#   -> fill in OPENAI_API_KEY, OAuth secrets, etc.

# 3. Start the dev stack (Postgres+pgvector, Redis, MinIO, judge0, api, worker, web)
make dev

# 4. Apply database migrations
make migrate

# 5. Seed sample data
make seed

# 6. Smoke-test the full pipeline on a sample video
make run-pipeline
```

- **API:** http://localhost:8000  (OpenAPI docs at `/docs`)
- **Web:** http://localhost:3000

### Windows (Docker Desktop + WSL2): space-free path required

Docker Desktop's WSL2 backend cannot bind-mount host paths that contain
**spaces** (it mis-translates e.g. `.../Interactive Cirriculum Engine/...` and
fails with `mkdir /run/desktop/mnt/host/d: file exists`). The dev stack uses
bind mounts (`../../:/app`, `.env`, `prometheus.dev.yml`, `judge0.conf`), so it
must be launched from a space-free path.

Fix (one-time per machine): create an NTFS junction with no spaces and launch
from it.

```powershell
# Run once (elevated not required for a junction):
cmd /c mklink /J D:\ice "D:\Genesys_Systems\Interactive Cirriculum Engine"

# Then start the stack from the junction (the helper script does this for you):
D:\ice\dev.ps1            # up -d + status
D:\ice\dev.ps1 down       # stop the stack
D:\ice\dev.ps1 logs       # tail logs
```

The junction is machine-local (not committed). Containers use named volumes for
the Python venv / node_modules, so the host `.venv` is unaffected. `make dev`
still works **only** if `make` is invoked from a space-free path such as
`D:\ice`.

## Development Workflow

We use **trunk-based GitHub Flow** with phase release tags. See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching strategy, PR rules, and the contract-first development order.

**Contract-first rule:** any change to `libs/contracts/` requires sign-off from both Aryan (producer) and Zubair (consumer). AI-package PRs must include a golden-set eval delta.

## Documentation

- [Architecture & system design](docs/architecture/)
- [Architecture Decision Records](docs/adr/)
- [OpenAPI spec (Appendix B)](docs/api/openapi.yaml)
- [Data model / ER (Appendix A)](docs/data-model/)
- [Canonical JSON contracts (§5.3)](docs/contracts/)
- [Research reading list (§7)](docs/research/)
- [Prompt library guide](docs/prompts/)
- [Operational runbooks](docs/runbooks/)
- [Onboarding](docs/onboarding/)

## Source Documents

- `PD - Project 1 Dynamic Video to Interactive Curriculum Engine.pdf` — Requirements (goals, motivation, functional/non-functional scope)
- `Interactive_Cirriculum_Engine.pdf` — Master Planning Document v1.0 (architecture, modules, roles, models, phases, evaluation)

## License

Proprietary. All rights reserved.
