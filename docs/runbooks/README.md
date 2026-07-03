# Operational Runbooks

Step-by-step procedures for operating the system. Each runbook is one file.

## Runbooks

- [deploy.md](deploy.md) — Release a new version (staging -> prod)
- [debug-pipeline.md](debug-pipeline.md) — Diagnose a stuck/failed curriculum
- [rotate-keys.md](rotate-keys.md) — Rotate JWT secret, OAuth secrets, OpenAI key
- [handle-gpt4o-outage.md](handle-gpt4o-outage.md) — Degrade to Llama/Qwen per §6.4
- [tenant-isolation-incident.md](tenant-isolation-incident.md) — Respond to a cross-tenant leak (risk E25)
- [sandbox-security-incident.md](sandbox-security-incident.md) — Respond to a sandbox escape (risk E19)

## On-call

Phase 5+ rotation. Sentry (`SENTRY_DSN`) pages on P0 errors. Grafana dashboards
in `infra/compose/` (port 3001, admin/grafana_dev).
