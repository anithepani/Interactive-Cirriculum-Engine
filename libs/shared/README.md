# ice-shared

Cross-cutting utilities consumed by every service (`apps/api`, `apps/worker`) and AI package:

- **`settings`** — typed environment config (`pydantic-settings`) loaded from `.env`. Single `Settings` object with sub-sections for DB, Redis, S3, judge0, LLM, ASR/OCR, pipeline caps.
- **`logging`** — structured JSON logging (`structlog`) with tenant + request-id context vars.
- **`tenant`** — `TenantContext` (async context var holding the current `tenant_id`), the seam for Postgres RLS (`SET app.tenant_id`) and S3 prefix scoping (`tenants/<id>/`).
- **`db`** — async SQLAlchemy 2.0 engine/session factory + pgvector setup + RLS helper.
- **`redis`** — Redis client + Celery broker handles.
- **`s3`** — MinIO/S3 client with tenant-scoped key helpers.
- **`retry`** — `tenacity` presets for pipeline steps (exponential backoff, per §6.4 degradation).
