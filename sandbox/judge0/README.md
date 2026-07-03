# judge0 (MVP sandbox)

Integration config for the judge0 code-execution sandbox.

## Dev

judge0 runs as a service in `infra/compose/docker-compose.dev.yml` on port 2358.
The `apps/api` + `apps/worker` services talk to it via `JUDGE0_URL`.

## Submission caps (risk E19)

Enforced per submission via `SANDBOX_*` env vars:
- `SANDBOX_CPU_LIMIT` (seconds)
- `SANDBOX_MEMORY_LIMIT` (KB)
- `SANDBOX_TIME_LIMIT` (wall-clock seconds)
- `SANDBOX_NETWORK_DISABLED=true`

## Languages

MVP: Python only (locked decision #3). JS/TS deferred to Phase 6.
