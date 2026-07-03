# Infra

Deployment and infrastructure-as-code for the Interactive Curriculum Engine.

- `docker/` — service Dockerfiles (`Dockerfile.api`, `.worker`, `.web`, `.gpu`)
- `compose/` — `docker-compose.dev.yml` (the Phase-0 bootable dev stack) + Prometheus config
- `k8s/` — production Kubernetes manifests (Phase 5)
- `terraform/` — cloud infrastructure as code (Phase 5)

## Dev stack

`make dev` runs `docker compose -f infra/compose/docker-compose.dev.yml up -d`, which boots:

| Service | Port | Purpose |
| --- | --- | --- |
| postgres (pgvector) | 5432 | relational DB + vector embeddings + RLS |
| redis | 6379 | cache + Celery broker/result |
| minio | 9000 / 9001 | tenant-scoped object storage (videos/frames/artifacts) |
| judge0 | 2358 | code-execution sandbox (M14 MVP) |
| api | 8000 | FastAPI (OpenAPI at `/docs`) |
| worker | — | Celery worker (pipeline orchestration) |
| prometheus | 9090 | metrics |
| grafana | 3001 | dashboards (admin/grafana_dev) |

Owner: **Zubair**
