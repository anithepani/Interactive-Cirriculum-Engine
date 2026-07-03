# Deploy Runbook

Release a new version: staging -> production. Phase 5+.

## Staging (on push to `main`)

1. CI (`deploy.yml`) builds + pushes images to GHCR (`ghcr.io/<org>/ice-{api,worker,web}:sha`).
2. Migrations run against the staging DB.
3. `kubectl rollout` (or `terraform apply`) updates staging.
4. Smoke tests: `/health`, a sample curriculum, eval latency.

## Production (on `release/v*` tag)

1. Require the `eval-regression.yml` artifact for this tag to be green.
2. CI builds + pushes semver-tagged images.
3. Migrations run against prod DB (reversible; `alembic downgrade` tested in CI).
4. Rollout with a canary (10% -> 50% -> 100%); monitor Grafana + Sentry.
5. Tag the release in GitHub with the phase summary.

## Rollback

```bash
kubectl rollout undo deployment/ice-api -n ice-prod
# or revert the migration if a schema change is the cause:
uv run alembic -c db/alembic.ini downgrade -1
```
