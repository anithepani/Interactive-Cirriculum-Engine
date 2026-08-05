#!/usr/bin/env bash
# ============================================================
# ICE — YouTube download health check (run on the prod VM)
#
# The PO Token provider sidecar (bgutil) is now the primary bot-detection
# bypass; cookies were dropped. This script:
#   1. Pings the pot-provider sidecar (must be reachable from the worker).
#   2. Functionally validates end-to-end by asking yt-dlp (inside the worker,
#      using the PO-token plugin + client rotation) to read a video that
#      YouTube blocks for naive anonymous clients.
#
# Exit codes:
#   0  downloads healthy
#   1  pot-provider unreachable OR yt-dlp still bot-blocked  (alert!)
#
# Wire to a periodic cron, e.g.:
#   0 6 * * * /opt/ice/infra/prod/scripts/check_youtube.sh >> /var/log/ice-youtube.log 2>&1 || \
#     curl -fsS -X POST "$ALERT_WEBHOOK" -d 'ICE YouTube download check FAILED'
# ============================================================
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/ice/infra/prod/docker-compose.prod.yml}"
POT_BASE_URL="${YT_POT_PROVIDER_BASE_URL:-http://pot-provider:4416}"
# Video that requires auth/PO-token for datacenter IPs (from the original prod failure).
TEST_VIDEO="${TEST_VIDEO:-https://www.youtube.com/watch?v=1aA1WGON49E}"

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

# --- 1. PO Token provider reachability (from inside the worker network) --------
echo "Pinging PO Token provider at $POT_BASE_URL/ping ..."
if compose exec -T worker curl -fsS "$POT_BASE_URL/ping" >/dev/null 2>&1; then
  echo "POT_PROVIDER_OK"
else
  echo "POT_PROVIDER_UNREACHABLE: $POT_BASE_URL not responding from worker"
  exit 1
fi

# --- 2. End-to-end functional probe using the application's exact options -----
echo "Validating YouTube extraction against $TEST_VIDEO ..."
if compose exec -T worker python /app/infra/prod/scripts/diagnose_youtube.py \
     --sample "$TEST_VIDEO" | grep -q '"phase": "media_sample", "status": "ok"'; then
  echo "YOUTUBE_OK"
  exit 0
else
  echo "YOUTUBE_BLOCKED: yt-dlp failed (PO token/client rotation exhausted)"
  exit 1
fi
