# ice-worker (Celery)

Hosts the async generation pipeline that orchestrates the AI modules M1-M10. Heavy
work runs here so session-time API calls stay fast (target <2s p95 eval, risk E17).

## Pipeline (master plan §4.1 data flow)

```
ingest -> ASR + OCR (parallel) -> multimodal fusion -> concept segmentation
       -> checkpoint placement -> exercise + test generation (validated)
       -> persist curriculum JSON -> mark ready
```

Each step is a Celery task; failures retry with exponential backoff (§6.4 degradation);
partial results flagged; low-confidence items surfaced to admin (UC-14). Every task
carries `tenant_id` for RLS + storage prefix isolation (§4.1 multi-tenancy note).

## Run (dev)

```bash
make dev        # starts the worker in the compose stack
# or directly:
uv run celery -A ice_worker.celery_app worker -l info
# flower dashboard:
uv run celery -A ice_worker.celery_app flower
```

## Structure

```
src/ice_worker/
  celery_app.py      Celery app + broker/result backend config
  tasks/             one module per pipeline stage (ingest, transcribe, vision,
                     segment, concepts, checkpoints, generate, validate)
  pipeline.py        the DAG wiring tasks together (chain/chord)
  budgets.py         per-curriculum token budget enforcement (cost control, E16)
```

Owner: **Zubair**. AI tasks delegate to `libs/ai/*` (Aryan/Ahmed own those).
