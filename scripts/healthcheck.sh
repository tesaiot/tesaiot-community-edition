#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# healthcheck.sh - probe each of the core services and print a status table.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

PASS=0; FAILN=0

# Print one row. name, status(ok|fail|warn), detail
row() {
  local name="$1" st="$2" detail="$3" mark color
  case "$st" in
    ok)   mark="UP   "; color="${C_GREEN}" ; PASS=$((PASS+1)) ;;
    warn) mark="WARN "; color="${C_YELLOW}";;
    *)    mark="DOWN "; color="${C_RED}"   ; FAILN=$((FAILN+1)) ;;
  esac
  printf "%b %-14s %b %s\n" "${color}${mark}${C_RESET}" "${name}" "${C_RESET}" "${detail}"
}

# Run a command inside a container; ok if it exits 0.
chk_exec() {  # name container cmd...
  local name="$1" c="$2"; shift 2
  if docker exec "$c" "$@" >/dev/null 2>&1; then row "$name" ok "container: $c"; else row "$name" fail "container: $c"; fi
}

step "TESAIoT Community Edition - health"
printf "%-20s %s\n" "SERVICE" "DETAIL"
printf -- "----------------------------------------------------------\n"

# Vault (sealed counts as warn).
if docker exec tesa-vault sh -c 'vault status >/dev/null 2>&1'; then
  row "vault" ok "unsealed + active"
elif docker exec tesa-vault sh -c 'wget -q -O- http://127.0.0.1:8200/v1/sys/health?sealedcode=200 >/dev/null 2>&1'; then
  row "vault" warn "API up but SEALED (run init-vault-pki.sh)"
else
  row "vault" fail "unreachable"
fi

# test -s: token must exist AND be non-empty (an empty leftover file is a fail).
chk_exec "vault-agent" tesa-vault-agent test -s /vault/token/api-token
chk_exec "mongodb"     tesa-mongodb mongosh --quiet --eval "db.runCommand({ping:1}).ok"
chk_exec "timescaledb" tesa-timescaledb pg_isready -U "$(env_get POSTGRES_USER || echo postgres)"
if docker exec tesa-redis sh -c "redis-cli -a \"$(env_get REDIS_PASSWORD)\" ping 2>/dev/null | grep -q PONG"; then
  row "redis" ok "PONG"
else
  row "redis" fail "no PONG"
fi

# API health endpoint.
if docker exec tesa-api curl -fsS http://localhost:5566/api/v1/health >/dev/null 2>&1; then
  row "api" ok "GET /api/v1/health"
else
  row "api" fail "health endpoint not 200"
fi

# Admin UI (its non-root nginx listens on 8080 in-container, not 80).
if docker exec tesa-admin-ui sh -c 'curl -fsS http://localhost:8080/health >/dev/null 2>&1 || curl -fsS http://localhost:8080/ >/dev/null 2>&1'; then
  row "admin-ui" ok "nginx serving SPA"
else
  row "admin-ui" fail "not serving"
fi

chk_exec "emqx"   tesa-emqx emqx ctl status
chk_exec "nginx"  tesa-nginx nginx -t
if docker exec tesa-apisix sh -c 'ps aux | grep -q "[o]penresty"'; then
  row "apisix" ok "gateway running"
else
  row "apisix" fail "openresty not running"
fi

# mqtt-bridge (no http endpoint; check the container is running).
if [ "$(docker inspect -f '{{.State.Running}}' tesa-mqtt-bridge 2>/dev/null)" = "true" ]; then
  row "mqtt-bridge" ok "running"
else
  row "mqtt-bridge" fail "not running"
fi

printf -- "----------------------------------------------------------\n"
step "Summary: ${PASS} up, ${FAILN} down"
[ "${FAILN}" -eq 0 ] || exit 1
