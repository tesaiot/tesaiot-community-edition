#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# preflight-check.sh - verify the host can run TESAIoT Community Edition.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

FAIL=0

step "Preflight checks"

# --- Docker engine ---------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  ok "docker found: $(docker --version 2>/dev/null | head -n1)"
else
  err "docker not installed - see https://docs.docker.com/engine/install/"
  FAIL=1
fi

# --- Docker Compose v2 -----------------------------------------------------
if docker compose version >/dev/null 2>&1; then
  ok "docker compose v2 found: $(docker compose version --short 2>/dev/null)"
else
  err "docker compose v2 plugin missing (the legacy 'docker-compose' is not supported)"
  FAIL=1
fi

# --- Daemon reachable ------------------------------------------------------
if docker info >/dev/null 2>&1; then
  ok "docker daemon reachable"
else
  err "cannot talk to docker daemon (is it running? are you in the 'docker' group?)"
  FAIL=1
fi

# --- Required CLI tools ----------------------------------------------------
# Hard requirements: generate-secrets.sh dies without openssl (secrets, TLS)
# and python3 (APISIX TLS-material + SNI patching).
for tool in openssl python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool found"
  else
    err "$tool not installed - required by generate-secrets.sh"
    FAIL=1
  fi
done
if command -v curl >/dev/null 2>&1; then
  ok "curl found"
else
  warn "curl not found (recommended; healthcheck/manual API probing use it)"
fi

# --- Ports free ------------------------------------------------------------
# Host ports the stack binds. We only warn (a port may be owned by a previous
# run of this same stack), so this never blocks a redeploy.
# Keep in sync with the published ports in docker-compose.yml:
#   LAN-facing : 80 443 9444 (nginx)  8883 8884 8084 (emqx TLS)  9443 (apisix)
#   loopback   : 8200 (vault)  1883 8083 18083 (emqx)  9080 9180 (apisix)
# (5566/api and 27017/mongodb are deliberately NOT published.)
PORTS="80 443 1883 8083 8084 8200 8883 8884 9080 9180 9443 9444 18083"
in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -lnt "( sport = :$1 )" 2>/dev/null | grep -q ":$1 "
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}
log "Checking host ports: ${PORTS}"
for p in ${PORTS}; do
  if in_use "$p"; then
    warn "port ${p} already in use (ok if it is this stack restarting)"
  fi
done

# --- Disk space ------------------------------------------------------------
AVAIL_KB="$(df -Pk "${ROOT_DIR}" | awk 'NR==2{print $4}')"
AVAIL_GB=$(( AVAIL_KB / 1024 / 1024 ))
if [ "${AVAIL_GB}" -ge 10 ]; then
  ok "disk space: ${AVAIL_GB} GB free"
else
  warn "only ${AVAIL_GB} GB free - 10+ GB recommended for images + data"
fi

# --- .env present ----------------------------------------------------------
if [ -f "${ENV_FILE}" ]; then
  ok ".env present"
  if grep -q "CHANGEME" "${ENV_FILE}"; then
    warn ".env still contains CHANGEME placeholders - run generate-secrets.sh or edit it"
  fi
  # Security-critical secrets must never ship as the public placeholder — hard fail.
  for crit in MTLS_GATEWAY_SECRET MONGODB_PASSWORD JWT_SECRET SECRET_KEY EMQX_WEBHOOK_SECRET; do
    if grep -qE "^${crit}=CHANGEME" "${ENV_FILE}"; then
      err "${crit} is still the CHANGEME placeholder - run generate-secrets.sh (fail-closed security secret)"
      FAIL=1
    fi
  done
else
  warn ".env not found - generate-secrets.sh will create it"
fi

# --- Rendered config templates ----------------------------------------------
# generate-secrets.sh renders config/**/*.tpl into the files docker-compose
# mounts. Missing renders on an existing install mean `docker compose up` was
# run without generate-secrets.sh (compose would bind-mount them as empty dirs).
if [ -f "${ENV_FILE}" ]; then
  for rendered in \
    "config/emqx/emqx.conf" \
    "config/emqx/auth-built-in-db-bootstrap.csv" \
    "config/apisix/config.yaml" \
    "config/apisix/apisix.yaml" \
    "config/nginx/conf.d/30-iot-mtls.conf"; do
    [ -f "${ROOT_DIR}/${rendered}" ] \
      || warn "${rendered} not rendered yet - run generate-secrets.sh before docker compose up"
  done
fi

step "Preflight result"
if [ "${FAIL}" -ne 0 ]; then
  die "Preflight failed - fix the errors above before continuing."
fi
ok "Host is ready."
