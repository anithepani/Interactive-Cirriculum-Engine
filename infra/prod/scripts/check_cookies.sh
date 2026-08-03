#!/usr/bin/env bash
# ============================================================
# ICE — YouTube cookie health check (run on the prod VM)
#
# 1. Warns if any youtube.com cookie expires within the refresh window.
# 2. Functionally validates the cookie by asking yt-dlp (inside the worker
#    container) to read a video that YouTube blocks for anonymous clients.
#
# Exit codes:
#   0  cookies valid (may still print EXPIRING warnings)
#   1  cookie file missing / invalid / bot-blocked  (alert!)
#
# Wire to weekly cron, e.g.:
#   0 6 * * 1  /opt/ice/infra/prod/scripts/check_cookies.sh >> /var/log/ice-cookies.log 2>&1 || \
#     curl -fsS -X POST "$ALERT_WEBHOOK" -d 'ICE YouTube cookie check FAILED'
# ============================================================
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/ice/infra/prod/docker-compose.prod.yml}"
COOKIE="${COOKIE:-/opt/ice/secrets/cookies.txt}"
IN_CONTAINER_COOKIE="${IN_CONTAINER_COOKIE:-/app/cookies.txt}"
REFRESH_INTERVAL="${YT_COOKIE_REFRESH_INTERVAL:-604800}"  # 7 days
# Video that requires auth for datacenter IPs (from the original prod failure).
TEST_VIDEO="${TEST_VIDEO:-https://www.youtube.com/watch?v=1aA1WGON49E}"

if [[ ! -f "$COOKIE" ]]; then
  echo "COOKIE_MISSING: $COOKIE not found on host"
  exit 1
fi

# --- 1. Expiry warning (Netscape field 5 = unix expiry; 0 = session cookie) ---
now="$(date +%s)"
soon="$((now + REFRESH_INTERVAL))"
awk -v soon="$soon" -v now="$now" '
  /youtube/ && $5 ~ /^[0-9]+$/ && $5 > 0 {
    if ($5 < now)  { print "EXPIRED: cookie " $6 " expired " $5 }
    else if ($5 < soon) { print "EXPIRING: cookie " $6 " expires " $5 }
  }
' "$COOKIE"

# --- 2. Functional probe through the worker container -------------------------
echo "Validating cookie against $TEST_VIDEO ..."
if docker compose -f "$COMPOSE_FILE" exec -T worker \
     yt-dlp --cookies "$IN_CONTAINER_COOKIE" --skip-download --quiet "$TEST_VIDEO"; then
  echo "COOKIE_OK"
  exit 0
else
  echo "COOKIE_INVALID: yt-dlp failed with the mounted cookie (expired or bot-blocked)"
  exit 1
fi
