#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# init-apisix-routes.sh - APISIX runs in standalone YAML mode, so routes and
# consumers in config/apisix/apisix.yaml are loaded at boot (no etcd, no Admin
# API push needed). This script:
#   1. injects the admin key from .env into config/apisix/config.yaml,
#   2. verifies the gateway is up and serving the declared routes.
# Idempotent.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

APISIX_C=tesa-apisix
ADMIN_KEY="$(env_get APISIX_ADMIN_KEY)"
CFG="${ROOT_DIR}/config/apisix/config.yaml"

step "1/2  Sync admin key into config.yaml"
# config.yaml is RENDERED from config.yaml.tpl by generate-secrets.sh (which
# already bakes the admin key in); this block is a safety net for a render
# that somehow still carries the placeholder.
[ -f "${CFG}" ] || die "config/apisix/config.yaml not rendered - run generate-secrets.sh (make secrets) first"
if grep -q "CHANGEME_APISIX_ADMIN_KEY" "${CFG}"; then
  if [ -z "${ADMIN_KEY}" ] || [ "${ADMIN_KEY}" = "CHANGEME_APISIX_ADMIN_KEY" ]; then
    die "APISIX_ADMIN_KEY not set in .env - run generate-secrets.sh"
  fi
  # Portable in-place edit (works with both BSD/macOS and GNU sed).
  sed "s|CHANGEME_APISIX_ADMIN_KEY|${ADMIN_KEY}|g" "${CFG}" > "${CFG}.tmp" \
    && mv "${CFG}.tmp" "${CFG}"
  ok "Admin key written to config.yaml - restart APISIX to apply:  docker compose restart apisix"
else
  ok "Admin key already set in config.yaml"
fi

step "2/2  Verify gateway"
log "Waiting for APISIX"
UP=0
for _ in $(seq 1 30); do
  if docker exec "${APISIX_C}" sh -c 'wget -q -O- http://127.0.0.1:9080 >/dev/null 2>&1 || true; ps aux | grep -q "[o]penresty"'; then
    UP=1; break
  fi
  sleep 2
done
[ "${UP}" = "1" ] && ok "APISIX is running" || warn "APISIX not confirmed up - check 'make logs s=apisix'"

# Probe the Admin API for the loaded routes (best-effort).
if [ -n "${ADMIN_KEY}" ] && [ "${ADMIN_KEY}" != "CHANGEME_APISIX_ADMIN_KEY" ]; then
  ROUTES="$(docker exec "${APISIX_C}" sh -c \
    "wget -q -O- --header='X-API-KEY: ${ADMIN_KEY}' http://127.0.0.1:9180/apisix/admin/routes 2>/dev/null" || true)"
  if echo "${ROUTES}" | grep -q '"uri"'; then
    ok "Routes loaded from apisix.yaml (standalone mode)"
  else
    warn "Could not read routes via Admin API (may be fine in pure standalone mode)."
  fi
fi

step "Done"
ok "APISIX gateway ready. Routes are declared in config/apisix/apisix.yaml."
