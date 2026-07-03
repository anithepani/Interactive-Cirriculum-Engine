# ice-api (M13 Backend API)

FastAPI (Python 3.11, async) service exposing the REST + WebSocket API: auth, sessions,
curriculum CRUD, evaluation. Multi-tenant with Postgres Row-Level Security from day one
(locked decision #5).

## Run (dev)

```bash
make dev        # starts compose stack including this service
# or directly:
uv run uvicorn ice_api.main:app --reload --port 8000
```

- **OpenAPI docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/health

## Structure

```
src/ice_api/
  main.py            FastAPI app factory + middleware (CORS, tenant, logging)
  deps.py            shared dependencies (DB session, current user, tenant context)
  auth/              OAuth (Google/GitHub) + JWT issuance, per-tenant
  routers/           curriculum, sessions, eval, progress, admin (instructor)
  ws/                WebSocket handlers (live eval feedback, session updates)
  middleware/        TenantMiddleware (binds tenant_id -> RLS), rate limiting
  models/            SQLAlchemy ORM models (mirror db/ schema)
  schemas/           request/response DTOs (re-export from ice_contracts where shared)
```

## Endpoints (from docs/api/openapi.yaml, §5.3.2)

- `POST /ai/curriculum/generate` (async -> curriculum_id)
- `GET /ai/curriculum/{id}`
- `POST /ai/evaluate`
- `POST /ai/regenerate`
- `GET /ai/adaptive/{session_id}`
- (internal) `POST /vision/extract`, `POST /nlp/segment`

Owner: **Zubair**
