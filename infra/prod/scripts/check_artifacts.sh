#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/ice/infra/prod/docker-compose.prod.yml}"
PUBLIC_ORIGIN="${MINIO_EXTERNAL_ENDPOINT:-https://4.247.144.148.sslip.io}"
BUCKET="${S3_BUCKET:-ice-artifacts}"
OBJECT_KEY="${1:?usage: check_artifacts.sh tenants/<tenant>/curricula/<curriculum>/recap.mp4}"

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

compose run --rm --no-deps --entrypoint /bin/sh minio-init -c \
  'mc alias set ice http://minio:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null && mc stat "ice/$S3_BUCKET/'"$OBJECT_KEY"'"'

headers="$(curl -fsS -D - -o /dev/null -H 'Range: bytes=0-1' \
  "$PUBLIC_ORIGIN/$BUCKET/$OBJECT_KEY")"
printf '%s\n' "$headers"
printf '%s\n' "$headers" | grep -Eq '^HTTP/[^ ]+ (200|206)'
printf '%s\n' "$headers" | grep -Eiq '^content-type: video/mp4'
