# Production Fix Deployment

This release changes the API, worker image, database schema, Caddy routing, and
MinIO bucket policy. Run commands from `/opt/ice` on the Azure VM. Replace the
example curriculum IDs and YouTube URLs with controlled test data.

## Preflight

```bash
git status --short
git rev-parse HEAD
docker compose -f infra/prod/docker-compose.prod.yml config --quiet
docker run --rm -v "$PWD/infra/prod/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2 caddy validate --config /etc/caddy/Caddyfile
docker compose -f infra/prod/docker-compose.prod.yml exec -T api \
  uv run --no-sync alembic -c db/alembic.ini current
```

Back up the affected tables before migration:

```bash
docker compose -f infra/prod/docker-compose.prod.yml exec -T api \
  uv run --no-sync python -c 'from ice_shared import settings; print(settings.database_url_resolved)'
# Use the corresponding Neon backup/branch workflow before continuing.
```

The migration deduplicates `sessions` by `(user_id, curriculum_id)`, preserving
the maximum resume/max-watched values and summing watch time.

## Build And Migrate

Build the worker because it is a Compose `build:` service and no longer has a
source bind mount:

```bash
docker compose -f infra/prod/docker-compose.prod.yml build --pull worker
docker compose -f infra/prod/docker-compose.prod.yml run --rm --no-deps worker \
  sh -lc 'test -f /app/apps/remotion/package-lock.json && \
  test -x /app/apps/remotion/node_modules/.bin/remotion && \
  cd /app/apps/remotion && ./node_modules/.bin/remotion compositions src/index.ts'
```

Expected composition: `MainComp`.

Apply the forward migration before starting the new API code:

```bash
docker compose -f infra/prod/docker-compose.prod.yml run --rm --no-deps api \
  uv run --no-sync alembic -c db/alembic.ini upgrade head
```

## Deploy

Set the external media origin in `/opt/ice/.env`:

```dotenv
MINIO_EXTERNAL_ENDPOINT=https://4.247.144.148.sslip.io
SIGNAL_VIDEO_REMOTION_PROJECT_DIR=/app/apps/remotion
SIGNAL_VIDEO_REMOTION_COMMAND=/app/apps/remotion/node_modules/.bin/remotion
```

Recreate the one-shot MinIO initializer, API, worker, and Caddy:

```bash
docker compose -f infra/prod/docker-compose.prod.yml up -d minio
docker compose -f infra/prod/docker-compose.prod.yml run --rm minio-init
docker compose -f infra/prod/docker-compose.prod.yml up -d --force-recreate api
docker compose -f infra/prod/docker-compose.prod.yml up -d --force-recreate worker
docker compose -f infra/prod/docker-compose.prod.yml up -d --force-recreate caddy
docker compose -f infra/prod/docker-compose.prod.yml ps
curl -fsS https://4.247.144.148.sslip.io/health
```

## Validate

Progress:

```bash
curl -fsS -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"position":12,"max_watched":12,"watched_delta":5}' \
  "https://4.247.144.148.sslip.io/api/v1/curricula/$CURRICULUM_ID/progress"
```

Repeat concurrently and confirm one session row exists. Verify an unknown or
other user's curriculum returns 404.

Artifacts:

```bash
infra/prod/scripts/check_artifacts.sh \
  "tenants/$TENANT_ID/curricula/$CURRICULUM_ID/recap.mp4"
```

Expected: object stat succeeds and the HTTPS range request returns `200` or
`206` with `Content-Type: video/mp4`.

DELETE:

```bash
curl -fsS -X DELETE -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://4.247.144.148.sslip.io/api/v1/curricula/$DELETE_TEST_ID"
docker compose -f infra/prod/docker-compose.prod.yml logs --since=10m api | \
  grep -E 'Error deleting curriculum|UndefinedColumnError' || true
```

Remotion:

```bash
docker compose -f infra/prod/docker-compose.prod.yml exec -T worker sh -lc \
  'cd /app/apps/remotion && ./node_modules/.bin/remotion compositions src/index.ts'
# Trigger one controlled signal video and inspect queued -> processing -> ready.
docker compose -f infra/prod/docker-compose.prod.yml logs --since=20m worker | \
  grep -E 'Rendering Remotion|Remotion render error|signal_video'
```

YouTube diagnostics must run before adding any authenticated fallback:

```bash
docker compose -f infra/prod/docker-compose.prod.yml exec -T worker \
  python /app/infra/prod/scripts/diagnose_youtube.py --sample --verbose \
  'https://www.youtube.com/watch?v=dQw4w9WgXcQ' \
  'https://www.youtube.com/watch?v=I2wURDqiXdM' \
  '<second-failing-python-url>' | tee /tmp/ice-youtube-matrix.jsonl
```

Only introduce cookies or another provider after comparing metadata and media
results by client and confirming that authentication changes the failing case.

## Rollback

Application and Caddy containers can be returned to their previous image/source
revision. Do not downgrade migration `0003` after new progress writes unless a
database restore is planned: deduplicated session rows cannot be reconstructed.
The new columns and unique index are safe to leave in place during an application
rollback. Restore the Neon backup/branch if the migration itself must be undone.
