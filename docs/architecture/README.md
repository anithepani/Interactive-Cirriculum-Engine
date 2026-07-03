# System Architecture

Living document; refined after Phase 0. Source of truth: the master plan
(`Interactive_Cirriculum_Engine.pdf`) section 4. This page summarizes it for
quick onboarding.

## High-level diagram (§4.1)

```
+------------------------------------------+
|              FRONTEND (Next.js Web App)   |
|  Video Player + Exercise Overlay + Dash   |
+---------------+--------------------------+
                | REST + WebSocket (SSE)
+---------------v--------------------------+
|            BACKEND API (FastAPI)          |
|  Auth - Sessions - Curriculum CRUD - Eval  |
|  (multi-tenant, row-level isolation)       |
+---+---------------+---------------+------+
    |               |               |
+---+------+   +----+----------+   +--+-----------+
| Postgres + |   | Async Task  |   | Code Sandbox |
| pgvector + |   | Queue       |   | judge0 ->    |
| RLS tenant |   | (Celery+    |   | Firecracker  |
| Redis cache|   |  Redis)     |   |              |
+------------+   +----+--------+   +--------------+
                      | orchestrates
        +-------------+----------------+
        v             v                v
+--------+----+  +-----+------+  +-----+--------+
| AI PIPELINE |  | VISION     |  | GENERATION   |
| ingest/ASR/ |  | OCR/key-   |  | exercises/   |
| segment/    |  | frames/    |  | tests/eval/  |
| concepts    |  | slides     |  | adapt        |
+----+--------+  +-----+------+  +-----+--------+
     |                 | fusion        |
     v                                 v
+-----------+                   +-----------+
| Knowledge |<------------------| Model     |
| Store     |                   | Layer     |
| (graph,   |                   | GPT-4o /  |
| curric.)  |                   | Whisper / |
+-----------+                   | Qwen /    |
                                | PaddleOCR |
                                +-----------+
```

## Data flow (§4.1 summary)

Video -> Ingestion -> (ASR + Vision) -> Multimodal fusion -> Concept segmentation
-> Checkpoint placement -> Exercise + test generation (validated) -> Persist
curriculum JSON -> Frontend plays -> Session -> Evaluation -> Adaptive controller
-> Progress store -> Dashboard.

## Modules (M1-M15)

| Module | Owner | Phase |
| --- | --- | --- |
| M1 Ingestion | Zubair/Ahmed | 1 |
| M2 Transcript (ASR) | Aryan | 1 |
| M3 Visual Extraction | Ahmed | 1 |
| M4 Lesson Structure | Aryan | 2 |
| M5 Concept Graph | Aryan | 2 |
| M6 Checkpoint Placement | Aryan | 2 |
| M7 Exercise Generation | Aryan | 3 |
| M8 Test Gen & Validation | Aryan | 3 |
| M9 Evaluation Engine | Aryan | 3 |
| M10 Adaptive Controller | Aryan | 4 |
| M11 Progress Tracker | Zubair | 4 |
| M12 Frontend | Zubair | 4 |
| M13 Backend API/DB | Zubair | 1-4 |
| M14 Code Sandbox | Zubair | 3 |
| M15 Monitoring | Zubair | 5 |

## Multi-tenancy (§4.1 note, risk E25)

Every record carries `tenant_id`. Postgres RLS policies enforce isolation. MinIO
buckets/prefixes are tenant-scoped (`tenants/<id>/`). judge0 submissions are tagged
with the tenant. Celery tasks carry tenant context.

## Async pipeline + session-time latency (risk E17)

The heavy generation pipeline is async (Celery). At session time, only fast
evaluation calls happen (target <2s p95). The full curriculum is pre-generated
before the learner starts a session.
