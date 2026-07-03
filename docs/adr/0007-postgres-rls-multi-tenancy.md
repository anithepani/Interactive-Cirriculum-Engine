# ADR 0007: Postgres Row-Level Security for Multi-Tenancy

- **Status:** Accepted (locked decision #5)
- **Date:** 2026-07
- **Deciders:** Zubair, Aryan, Ahmed
- **Master plan ref:** Locked Decisions, §4.1, risk E25

## Context

Multi-tenant cloud with row-level data isolation + auth from day one is a locked
decision. Cross-tenant leakage is a P0 security bug (risk E25).

## Decision

Every tenant-scoped table carries `tenant_id`. Postgres RLS policies enforce
isolation: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`. The app
sets `app.tenant_id` per session/request via `libs/shared/tenant.py`. S3 prefixes
are tenant-scoped (`tenants/<id>/`); judge0 submissions are tenant-tagged.

## Consequences

- Positive: isolation enforced at the DB, not just the app; auditable
- Negative: every query must set the GUC; CI enforces via `scripts/check_rls.py` + `tests/integration/test_rls.py`
- Risks: E25 (mitigated by RLS + FORCE + audit_log)
