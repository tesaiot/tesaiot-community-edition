#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# unseal-vault.sh - manually unseal a sealed Vault (e.g. after a host reboot)
# using the Shamir key shares stored in .env by init-vault-pki.sh.
#
# Normally the vault-agent side-car self-unseals (see VAULT_UNSEAL_KEYS in
# docker-compose.yml); this script is the manual recovery path when that is
# opted out of, or when vault-agent itself is down. Idempotent: a Vault that
# is already unsealed is left alone.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

VAULT_C=tesa-vault

step "Vault seal status"
# Capture-then-parse: `vault status` exits 2 when sealed, which must not be
# allowed to corrupt the parsed value under pipefail (see init-vault-pki.sh).
STATUS_JSON="$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
  sh -c 'vault status -format=json 2>/dev/null' || true)"
[ -n "${STATUS_JSON}" ] || die "Vault API unreachable - is the tesa-vault container running? (make up)"
INITED="$(printf '%s' "${STATUS_JSON}" | grep -o '"initialized":[^,]*' | cut -d: -f2 | tr -d ' ' || true)"
SEALED="$(printf '%s' "${STATUS_JSON}" | grep -o '"sealed":[^,]*' | cut -d: -f2 | tr -d ' ' || true)"

[ "${INITED}" = "true" ] || die "Vault is not initialised yet - run: make init-pki"
if [ "${SEALED}" = "false" ]; then
  ok "Vault is already unsealed - nothing to do."
  exit 0
fi

log "Vault is sealed - unsealing with the key shares from .env"
K1="$(env_get VAULT_UNSEAL_KEY_1 || true)"
K2="$(env_get VAULT_UNSEAL_KEY_2 || true)"
K3="$(env_get VAULT_UNSEAL_KEY_3 || true)"
SUBMITTED=0
for k in "${K1}" "${K2}" "${K3}"; do
  [ -n "${k}" ] || continue
  docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
    vault operator unseal "${k}" >/dev/null
  SUBMITTED=$((SUBMITTED + 1))
  # Stop as soon as the threshold (2 of 3) is met.
  STATUS_JSON="$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
    sh -c 'vault status -format=json 2>/dev/null' || true)"
  if printf '%s' "${STATUS_JSON}" | grep -q '"sealed":false'; then
    ok "Vault unsealed (${SUBMITTED} key share(s) submitted)."
    log "If services were waiting on Vault, give them a moment or run: docker compose restart vault-agent api"
    exit 0
  fi
done

[ "${SUBMITTED}" -gt 0 ] \
  && die "Submitted ${SUBMITTED} key share(s) but Vault is still sealed - check VAULT_UNSEAL_KEY_* in .env." \
  || die "No VAULT_UNSEAL_KEY_* found in .env - restore .env from backup (without the key shares this Vault cannot be unsealed)."
