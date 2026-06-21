#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# install.sh - one-command bootstrap for TESAIoT Community Edition.
#
#   preflight -> secrets -> infra (vault/dbs) -> vault PKI -> db init ->
#   restart cert-dependent svcs -> bring up app -> emqx + apisix -> health
#
# Safe to re-run. Pass --domain=example.com on first run to wire the domain.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

DOMAIN_ARG=""
# Pre-built mode: pull published images instead of building from source.
# Enable with --prebuilt or TESAIOT_PREBUILT=1. Falls back to a source build if
# the registry images are unavailable, so a fresh checkout always installs.
PREBUILT="${TESAIOT_PREBUILT:-0}"
for arg in "$@"; do
  case "$arg" in
    --domain=*) DOMAIN_ARG="$arg" ;;
    --prebuilt) PREBUILT=1 ;;
    *) ;;
  esac
done

banner() { printf "\n%b\n" "${C_BOLD}${C_BLUE}######## $* ########${C_RESET}"; }

# ---------------------------------------------------------------------------
banner "STEP 1  Preflight"
bash "${SCRIPT_DIR}/preflight-check.sh"

# ---------------------------------------------------------------------------
banner "STEP 2  Secrets + first-run TLS"
# Surface the domain choice up front. DOMAIN is the single source of truth for
# the public hostname (TLS cert CN/SAN + TESA_PUBLIC_* URLs); --domain wires it
# everywhere. If none is given on a fresh install we fall back to localhost.
if [ -n "${DOMAIN_ARG}" ]; then
  ok "Using domain: ${DOMAIN_ARG#--domain=} (wires TLS cert CN/SAN + public API/MQTT URLs)."
elif [ ! -f "${ENV_FILE}" ]; then
  warn "No --domain given: defaulting DOMAIN=localhost (evaluation mode)."
  warn "For a real host, re-run: make install DOMAIN=iot.yourcompany.com  (and point a DNS A-record at this host)."
fi
# Always pass --domain through: generate-secrets.sh applies it idempotently
# (re-derives EMQX_CERT_*/TESA_PUBLIC_*/ADMIN_EMAIL/BRIDGE_API_USER + APISIX
# snis) without regenerating secrets, so re-running with a new --domain on an
# existing .env actually changes the domain instead of being silently skipped.
if [ ! -f "${ENV_FILE}" ]; then
  bash "${SCRIPT_DIR}/generate-secrets.sh" "${DOMAIN_ARG}"
else
  ok ".env already exists - keeping current secrets (delete it to regenerate)"
  if [ -n "${DOMAIN_ARG}" ]; then
    CUR_DOMAIN="$(domain)"
    NEW_DOMAIN="${DOMAIN_ARG#--domain=}"
    [ "${CUR_DOMAIN}" != "${NEW_DOMAIN}" ] \
      && warn ".env DOMAIN='${CUR_DOMAIN}' differs from --domain='${NEW_DOMAIN}'; re-applying domain wiring."
  fi
  # Re-apply domain (if any) and ensure keyfile + TLS + rendered configs exist.
  bash "${SCRIPT_DIR}/generate-secrets.sh" "${DOMAIN_ARG}"
fi

# ---------------------------------------------------------------------------
if [ "${PREBUILT}" = "1" ]; then
  banner "STEP 3  Pull pre-built images"
  ok "Pre-built mode: pulling published images (api, admin-ui, mqtt-bridge)."
  if ! compose pull api admin-ui mqtt-bridge; then
    warn "Could not pull pre-built images (not published, private, or offline)."
    warn "Falling back to building from source."
    compose build
  fi
else
  banner "STEP 3  Build images"
  compose build
fi

# ---------------------------------------------------------------------------
banner "STEP 4  Bring up infrastructure (vault, dbs, redis)"
compose up -d vault mongodb timescaledb redis
log "Waiting for vault + databases to report healthy..."
for svc in vault mongodb timescaledb redis; do
  for _ in $(seq 1 60); do
    state="$(docker inspect -f '{{.State.Health.Status}}' "tesa-${svc}" 2>/dev/null || echo starting)"
    [ "${state}" = "healthy" ] && break
    sleep 3
  done
  ok "tesa-${svc}: ${state:-unknown}"
done

# ---------------------------------------------------------------------------
banner "STEP 5  Initialise Vault PKI"
bash "${SCRIPT_DIR}/init-vault-pki.sh"

# ---------------------------------------------------------------------------
banner "STEP 6  Start Vault Agent (renders certs from PKI)"
compose up -d vault-agent
log "Waiting for the API token sink + EMQX certs..."
TOKEN_OK=0
for _ in $(seq 1 40); do
  if docker exec tesa-vault-agent test -s /vault/token/api-token >/dev/null 2>&1; then
    TOKEN_OK=1; break
  fi
  sleep 3
done
# Fail HARD here: without the token sink the api's depends_on can never be
# satisfied, so continuing would just fail later with a less useful error.
if [ "${TOKEN_OK}" -ne 1 ]; then
  err "vault-agent did not produce a Vault token within 120s."
  err "Check: make logs s=vault-agent   (typical cause: AppRole creds missing - re-run make init-pki)"
  die "Install aborted at STEP 6."
fi
ok "vault-agent producing tokens/certs"

# ---------------------------------------------------------------------------
banner "STEP 7  Initialise databases (replica set + hypertable)"
bash "${SCRIPT_DIR}/init-databases.sh"

# ---------------------------------------------------------------------------
banner "STEP 8  Bring up application tier"
compose up -d api
log "Waiting for the API to become healthy (seeds bootstrap admin)..."
for _ in $(seq 1 60); do
  state="$(docker inspect -f '{{.State.Health.Status}}' tesa-api 2>/dev/null || echo starting)"
  [ "${state}" = "healthy" ] && break
  sleep 3
done
ok "tesa-api: ${state:-unknown}"

compose up -d emqx admin-ui apisix mqtt-bridge nginx

# ---------------------------------------------------------------------------
banner "STEP 9  Provision broker + gateway"
bash "${SCRIPT_DIR}/init-emqx.sh"        || warn "EMQX provisioning had warnings"
bash "${SCRIPT_DIR}/init-apisix-routes.sh" || warn "APISIX provisioning had warnings"
# apisix may need a restart to pick up the admin key written above.
compose restart apisix >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
banner "STEP 10  Health check"
sleep 8
# Containers can legitimately still be warming up on slow hosts: retry the
# whole probe a few times, but if it STILL fails, fail the install loudly
# instead of printing INSTALL COMPLETE over a broken stack.
HEALTH_OK=0
for attempt in 1 2 3; do
  if bash "${SCRIPT_DIR}/healthcheck.sh"; then HEALTH_OK=1; break; fi
  [ "${attempt}" -lt 3 ] && { log "Some services not healthy yet - retrying in 20s (${attempt}/3)..."; sleep 20; }
done
if [ "${HEALTH_OK}" -ne 1 ]; then
  err "Health check still failing after 3 attempts. The stack is NOT fully up."
  err "Inspect the failing rows above, then: make logs s=<service>   and re-check with: make health"
  die "Install FAILED at STEP 10."
fi

DOMAIN_VAL="$(domain)"
banner "INSTALL COMPLETE"
cat <<EOF

  Admin UI       :  https://${DOMAIN_VAL}/          (via nginx 443)
  API            :  https://${DOMAIN_VAL}/api/v1/   (internal-only :5566 - not published on the host)
  IoT mTLS ingest:  https://${DOMAIN_VAL}:9444/
  EMQX dashboard :  http://localhost:18083          (user: admin)
  APISIX gateway :  http://localhost:9080  (admin :9180)
  Vault UI       :  http://localhost:8200/ui

  Bootstrap admin login is ADMIN_EMAIL / ADMIN_PASSWORD from .env.
  Keep .env safe - it holds the Vault unseal keys + root token.

EOF
