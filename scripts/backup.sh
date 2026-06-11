#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# backup.sh - dump MongoDB + TimescaleDB, snapshot the Vault + EMQX data
# volumes, and archive the config/secrets needed to restore (.env, mongo
# keyfile, TLS, vault-agent approle/token, rendered config files).
#
# Output: ./backups/tesaiot-community-edition-<timestamp>.tar.gz
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

TS="$(date +%Y%m%d-%H%M%S)"
BK_DIR="${ROOT_DIR}/backups"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
mkdir -p "${BK_DIR}"

MROOT_USER="$(env_get MONGO_INITDB_ROOT_USERNAME)"
MROOT_PASS="$(env_get MONGO_INITDB_ROOT_PASSWORD)"
PG_USER="$(env_get POSTGRES_USER)"; PG_USER="${PG_USER:-postgres}"
PG_DB="$(env_get POSTGRES_DB)"; PG_DB="${PG_DB:-tesa_telemetry}"

# Resolve the real (project-prefixed) name of a named volume from the running
# container that mounts it, so this works whatever the compose project name is.
volume_of() {  # container  mount-destination
  docker inspect "$1" --format \
    '{{ range .Mounts }}{{ if eq .Destination "'"$2"'" }}{{ .Name }}{{ end }}{{ end }}' 2>/dev/null
}

step "1/4  MongoDB dump"
docker exec tesa-mongodb sh -c \
  "mongodump --quiet -u '${MROOT_USER}' -p '${MROOT_PASS}' --authenticationDatabase admin --archive --gzip" \
  > "${WORK}/mongodb.archive.gz"
ok "mongodump -> mongodb.archive.gz ($(du -h "${WORK}/mongodb.archive.gz" | cut -f1))"

step "2/4  TimescaleDB dump"
docker exec tesa-timescaledb sh -c \
  "pg_dump -U '${PG_USER}' -d '${PG_DB}' -Fc" > "${WORK}/timescaledb.dump"
ok "pg_dump -> timescaledb.dump ($(du -h "${WORK}/timescaledb.dump" | cut -f1))"

step "3/4  Volume snapshots (vault-data, emqx-data)"
# vault-data holds the WHOLE PKI (root + intermediate CA keys, issued-cert
# index, KV device certs). Without it a restore can only rebuild a NEW CA and
# every issued device cert dies. emqx-data holds the built-in auth DB +
# retained messages. Snapshotted via a throwaway container that tars the
# volume contents (file-storage backend; a live snapshot is crash-consistent,
# which is fine at this scale - stop the stack first for a bit-exact copy).
for spec in "tesa-vault:/vault/data:vault-data" "tesa-emqx:/opt/emqx/data:emqx-data"; do
  C="${spec%%:*}"; rest="${spec#*:}"; DEST="${rest%:*}"; LABEL="${rest##*:}"
  VOL="$(volume_of "${C}" "${DEST}")"
  if [ -n "${VOL}" ]; then
    docker run --rm -v "${VOL}:/data:ro" -v "${WORK}:/out" alpine \
      tar -czf "/out/${LABEL}.tar.gz" -C /data .
    ok "${LABEL} volume snapshot -> ${LABEL}.tar.gz ($(du -h "${WORK}/${LABEL}.tar.gz" | cut -f1))"
  else
    warn "could not resolve the ${LABEL} volume from container ${C} (is it running?) - SKIPPED"
  fi
done

step "4/4  Config + secrets"
mkdir -p "${WORK}/config"
cp -a "${ENV_FILE}" "${WORK}/.env" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/mongodb/mongodb-keyfile" "${WORK}/config/" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/tls" "${WORK}/config/tls" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/vault-agent/secrets-unified" "${WORK}/config/secrets-unified" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/vault-agent/token-api" "${WORK}/config/token-api" 2>/dev/null || true
# Rendered config files (from the *.tpl templates). Restoring these alongside
# .env keeps the rendered secrets and the .env values consistent without
# having to re-run generate-secrets.sh mid-restore.
mkdir -p "${WORK}/config/rendered/emqx" "${WORK}/config/rendered/apisix" "${WORK}/config/rendered/nginx-conf.d"
cp -a "${ROOT_DIR}/config/emqx/emqx.conf"                        "${WORK}/config/rendered/emqx/" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/emqx/auth-built-in-db-bootstrap.csv"   "${WORK}/config/rendered/emqx/" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/apisix/config.yaml"                    "${WORK}/config/rendered/apisix/" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/apisix/apisix.yaml"                    "${WORK}/config/rendered/apisix/" 2>/dev/null || true
cp -a "${ROOT_DIR}/config/nginx/conf.d/30-iot-mtls.conf"         "${WORK}/config/rendered/nginx-conf.d/" 2>/dev/null || true
ok "config + secrets staged"

ARCHIVE="${BK_DIR}/tesaiot-community-edition-${TS}.tar.gz"
tar -czf "${ARCHIVE}" -C "${WORK}" .
chmod 600 "${ARCHIVE}"

step "Done"
ok "Backup written: ${ARCHIVE}"
warn "This archive contains SECRETS (.env, keys, the whole Vault CA). Store it securely."
