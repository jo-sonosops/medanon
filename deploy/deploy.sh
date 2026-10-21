#!/usr/bin/env bash
# Deploy a medanon image on this host: pull, swap, health check, roll back on failure.
# Usage: deploy/deploy.sh ghcr.io/<owner>/medanon:sha-1a2b3c4
#
# Known limitation: there is a few seconds of downtime during the swap.
# A blue/green setup (two containers behind a proxy) would remove it.
set -euo pipefail

IMAGE="${1:?usage: deploy.sh <image:tag>}"
NAME="medanon"
PORT="${MEDANON_PORT:-8080}"
ENV_FILE="${MEDANON_ENV_FILE:-/var/lib/medanon/env}"
HEALTH_URL="http://127.0.0.1:${PORT}/healthz"

log() { echo "[deploy] $*"; }

run_container() {
  docker run -d --name "$NAME" \
    --restart unless-stopped \
    -p "127.0.0.1:${PORT}:8080" \
    --env-file "$ENV_FILE" \
    --read-only --tmpfs /tmp:rw,size=64m \
    --cap-drop ALL --security-opt no-new-privileges:true \
    --memory 512m --pids-limit 256 \
    "$1" >/dev/null
}

wait_healthy() {
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

if [ ! -r "$ENV_FILE" ]; then
  log "cannot read $ENV_FILE (needs MEDANON_SALT). See README, NixOS setup."
  exit 1
fi

PREVIOUS="$(docker inspect --format '{{.Config.Image}}' "$NAME" 2>/dev/null || true)"
log "running now: ${PREVIOUS:-nothing}"
log "deploying:   $IMAGE"

docker pull "$IMAGE"
docker rm -f "$NAME" >/dev/null 2>&1 || true
run_container "$IMAGE"

if wait_healthy; then
  log "healthy: $(curl -fsS "http://127.0.0.1:${PORT}/version")"
  exit 0
fi

log "health check failed after 30s. Last container logs:"
docker logs --tail 50 "$NAME" 2>&1 || true
docker rm -f "$NAME" >/dev/null 2>&1 || true

if [ -n "$PREVIOUS" ]; then
  log "rolling back to $PREVIOUS"
  run_container "$PREVIOUS"
  if wait_healthy; then
    log "rollback healthy"
  else
    log "rollback is unhealthy too. Escalate: see docs/runbooks/medanon-down.md"
  fi
else
  log "no previous version to roll back to"
fi
exit 1
