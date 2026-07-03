# Data Schema (ER) - Appendix A

The 15 tenant-scoped tables (master plan §5.3.3). All carry `tenant_id` and are
protected by Postgres Row-Level Security keyed on `app.tenant_id` (risk E25).
Baseline migration: [`db/migrations/0001_baseline.py`](../../db/migrations/0001_baseline.py).

## Entity relationships

```
tenants 1---* users
tenants 1---* curricula
curricula 1---* segments
curricula 1---* concepts
concepts *---* concept_edges (via src_concept_id / dst_concept_id)
segments 1---* exercises
exercises 1---* tests
exercises 1---* eval_results
curricula 1---* sessions
sessions 1---* session_events
sessions 1---* eval_results
users 1---* sessions
users 1---* skill_model
curricula 1---* skill_model
curricula 1---* artifacts
prompt_versions (global, not tenant-scoped)
audit_log (tenant-scoped for security audit, E25)
```

## Tables

| # | Table | Purpose | Key columns |
| --- | --- | --- | --- |
| 1 | `tenants` | Isolated customer | id, name, slug, token_budget |
| 2 | `users` | Learner/instructor/admin | tenant_id, email, role, oauth_* |
| 3 | `curricula` | One interactive course per video | tenant_id, video_ref, status, content_hash |
| 4 | `segments` | Topic segments (M4) | curriculum_id, start, end, title, structuredness |
| 5 | `concepts` | Concept nodes (M5) | curriculum_id, label, difficulty, embedding (vector) |
| 6 | `concept_edges` | Prerequisite/dependency edges | src, dst, relation |
| 7 | `exercises` | MCQ/coding/debug/conceptual (M7) | segment_id, concept_id, type, payload (JSONB) |
| 8 | `tests` | Visible + hidden test cases (M8) | exercise_id, is_visible, code, mutation_score |
| 9 | `sessions` | One learner's run through a curriculum | user_id, curriculum_id, resume_ts |
| 10 | `session_events` | Play/pause/submit events | session_id, ts, kind, payload |
| 11 | `eval_results` | Verdict per attempt (M9) | exercise_id, session_id, verdict, score, anti_cheat_flag |
| 12 | `skill_model` | Per-concept mastery (M11) | user_id, curriculum_id, mastery (JSONB) |
| 13 | `artifacts` | S3 pointers to video/audio/frames/etc | curriculum_id, kind, s3_key |
| 14 | `prompt_versions` | Versioned prompts (Appendix C) | name, version, model, template |
| 15 | `audit_log` | Security audit trail (E25) | tenant_id, actor_user_id, action, target_* |

## pgvector

`concepts.embedding` is a `vector(1024)` (BGE-M3 dimensionality) with an IVFFlat
index for similarity search (concept dedup, related-concept lookup).

Owner: **Zubair**
