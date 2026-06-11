#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# teardown.sh - stop and remove the stack.
#   (default)        stop + remove containers and networks (DATA KEPT)
#   --volumes        also delete named volumes (DESTROYS ALL DATA)
#   --purge          --volumes + delete generated secrets (.env, certs, keyfile)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

MODE="containers"
for arg in "$@"; do
  case "$arg" in
    --volumes) MODE="volumes" ;;
    --purge)   MODE="purge" ;;
    *) die "unknown arg: $arg (use --volumes or --purge)" ;;
  esac
done

confirm() {
  printf "%b" "${C_YELLOW}$1 [y/N]: ${C_RESET}"
  read -r ans
  case "${ans}" in [yY]|[yY][eE][sS]) return 0 ;; *) return 1 ;; esac
}

case "${MODE}" in
  containers)
    step "Stopping and removing containers + networks (data kept)"
    compose down
    ok "Stack stopped. Volumes preserved. Bring back up with: make up"
    ;;
  volumes)
    step "Removing containers + networks + VOLUMES (all data lost)"
    confirm "This DELETES all database + vault data. Continue?" || die "aborted"
    compose down -v
    ok "Stack and data volumes removed."
    ;;
  purge)
    step "Full purge: containers + volumes + generated secrets"
    confirm "This DELETES data AND .env/certs/keyfile/rendered configs. Continue?" || die "aborted"
    compose down -v
    rm -f "${ENV_FILE}"
    rm -f "${ROOT_DIR}/config/mongodb/mongodb-keyfile"
    rm -f "${ROOT_DIR}/config/tls/server-cert.pem" \
          "${ROOT_DIR}/config/tls/server-key.pem" \
          "${ROOT_DIR}/config/tls/ca-bundle.pem"
    # Rendered config files (generate-secrets.sh re-renders them from the
    # committed *.tpl templates on the next install). Deleting them here is
    # what makes purge+reinstall safe: stale renders can't carry secrets that
    # no longer match the regenerated .env.
    rm -f "${ROOT_DIR}/config/emqx/emqx.conf" \
          "${ROOT_DIR}/config/emqx/auth-built-in-db-bootstrap.csv" \
          "${ROOT_DIR}/config/apisix/config.yaml" \
          "${ROOT_DIR}/config/apisix/apisix.yaml" \
          "${ROOT_DIR}/config/nginx/conf.d/30-iot-mtls.conf"
    # Generated Vault Agent credentials. DELETE the files (an empty truncated
    # api-token would still satisfy a naive `cat` healthcheck; the compose
    # healthcheck uses `test -s` and a missing file fails it correctly).
    rm -f "${ROOT_DIR}/config/vault-agent/secrets-unified/role-id" \
          "${ROOT_DIR}/config/vault-agent/secrets-unified/secret-id" \
          "${ROOT_DIR}/config/vault-agent/token-api/api-token" \
          "${ROOT_DIR}/config/vault-agent/token-api/api-token-info.json"
    ok "Purged. Next install starts from scratch: make install"
    ;;
esac
