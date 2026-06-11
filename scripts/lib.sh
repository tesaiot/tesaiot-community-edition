#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Shared helpers for the TESAIoT Community Edition scripts. Source, don't execute.

# Resolve repo root regardless of the caller's CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
# shellcheck disable=SC2034  # consumed by sourcing scripts (generate-secrets.sh)
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"

# ---- pretty logging -------------------------------------------------------
if [ -t 1 ]; then
  C_RESET="\033[0m"; C_GREEN="\033[32m"; C_YELLOW="\033[33m"
  C_RED="\033[31m"; C_BLUE="\033[34m"; C_BOLD="\033[1m"
else
  C_RESET=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_BLUE=""; C_BOLD=""
fi

log()  { printf "%b\n" "${C_BLUE}[*]${C_RESET} $*"; }
ok()   { printf "%b\n" "${C_GREEN}[ok]${C_RESET} $*"; }
warn() { printf "%b\n" "${C_YELLOW}[!]${C_RESET} $*" >&2; }
err()  { printf "%b\n" "${C_RED}[x]${C_RESET} $*" >&2; }
die()  { err "$*"; exit 1; }
step() { printf "\n%b\n" "${C_BOLD}==> $*${C_RESET}"; }

# ---- docker compose wrapper (v2 only) -------------------------------------
compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

# ---- env helpers ----------------------------------------------------------
require_env_file() {
  [ -f "${ENV_FILE}" ] || die ".env not found. Run: ./scripts/generate-secrets.sh"
}

# Read a single KEY from .env (no sourcing, avoids surprises).
env_get() {
  local key="$1"
  [ -f "${ENV_FILE}" ] || return 1
  grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2-
}

# Random URL-safe secret of N characters (default 32).
gen_secret() {
  local bytes="${1:-32}" out=""
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 "${bytes}" | tr -d '\n=/+' | cut -c1-"${bytes}"
  else
    # Fallback without openssl: full-entropy alphanumerics (~5.95 bits/char).
    # (The previous hex fallback halved the entropy: N hex chars = N/2 bytes.)
    # Loop until we have N chars; head reads a bounded amount so this never
    # blocks and never trips `set -o pipefail` with a SIGPIPE.
    while [ "${#out}" -lt "${bytes}" ]; do
      out="${out}$(head -c $((bytes * 8)) /dev/urandom | tr -dc 'A-Za-z0-9')"
    done
    printf '%s' "${out}" | cut -c1-"${bytes}"
  fi
}

# DOMAIN with localhost default.
domain() { env_get DOMAIN 2>/dev/null || echo localhost; }
