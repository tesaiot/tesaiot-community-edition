#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# restore.sh <backup.tar.gz> - restore config/secrets (works even with the
# stack DOWN - this is what a fresh-host restore runs FIRST), restore the
# Vault/EMQX volume snapshots, then load the MongoDB and TimescaleDB dumps
# into the running databases.
#
# Fresh-host order (see docs/en/backup-restore.md):
#     git clone ... && cd tesaiot-community-edition
#     ./scripts/restore.sh <archive>     # lays down .env/keyfile/configs/volumes
#     make build && make up
#     ./scripts/restore.sh <archive>     # now the DB dumps load too
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

ARCHIVE="${1:-}"
[ -n "${ARCHIVE}" ] || die "usage: restore.sh <backup.tar.gz>"
[ -f "${ARCHIVE}" ] || die "no such file: ${ARCHIVE}"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

container_running() {  # name
  [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]
}

# Resolve the project-prefixed name of a named volume from the container that
# mounts it (works on stopped containers too; empty if the container is gone).
volume_of() {  # container  mount-destination
  docker inspect "$1" --format \
    '{{ range .Mounts }}{{ if eq .Destination "'"$2"'" }}{{ .Name }}{{ end }}{{ end }}' 2>/dev/null
}

step "1/5  Extract archive"
tar -xzf "${ARCHIVE}" -C "${WORK}"
ok "extracted to temp dir"

step "2/5  Restore config + secrets"
if [ -f "${WORK}/.env" ]; then
  if [ -f "${ENV_FILE}" ]; then
    cp -a "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%s)"
    warn "existing .env backed up before overwrite"
  fi
  cp -a "${WORK}/.env" "${ENV_FILE}"; chmod 600 "${ENV_FILE}"
fi
[ -f "${WORK}/config/mongodb-keyfile" ] && cp -a "${WORK}/config/mongodb-keyfile" "${ROOT_DIR}/config/mongodb/mongodb-keyfile"
[ -d "${WORK}/config/tls" ] && cp -a "${WORK}/config/tls/." "${ROOT_DIR}/config/tls/"
[ -d "${WORK}/config/secrets-unified" ] && cp -a "${WORK}/config/secrets-unified/." "${ROOT_DIR}/config/vault-agent/secrets-unified/"
[ -d "${WORK}/config/token-api" ] && cp -a "${WORK}/config/token-api/." "${ROOT_DIR}/config/vault-agent/token-api/"
# Rendered config files (generate-secrets.sh renders these from *.tpl; the
# backup carries them so the restored .env and rendered secrets stay in sync).
if [ -d "${WORK}/config/rendered" ]; then
  cp -a "${WORK}/config/rendered/emqx/."         "${ROOT_DIR}/config/emqx/"         2>/dev/null || true
  cp -a "${WORK}/config/rendered/apisix/."       "${ROOT_DIR}/config/apisix/"       2>/dev/null || true
  cp -a "${WORK}/config/rendered/nginx-conf.d/." "${ROOT_DIR}/config/nginx/conf.d/" 2>/dev/null || true
  ok "rendered config files restored"
else
  warn "no rendered configs in this backup (older archive) - run generate-secrets.sh after restoring .env"
fi
ok "config + secrets restored"

require_env_file
MROOT_USER="$(env_get MONGO_INITDB_ROOT_USERNAME)"
MROOT_PASS="$(env_get MONGO_INITDB_ROOT_PASSWORD)"
PG_USER="$(env_get POSTGRES_USER)"; PG_USER="${PG_USER:-postgres}"
PG_DB="$(env_get POSTGRES_DB)"; PG_DB="${PG_DB:-tesa_telemetry}"

step "3/5  Restore volume snapshots (vault-data, emqx-data)"
# The owning container must NOT be running while its volume is overwritten.
for spec in "tesa-vault:/vault/data:vault-data" "tesa-emqx:/opt/emqx/data:emqx-data"; do
  C="${spec%%:*}"; rest="${spec#*:}"; DEST="${rest%:*}"; LABEL="${rest##*:}"
  SNAP="${WORK}/${LABEL}.tar.gz"
  if [ ! -f "${SNAP}" ]; then
    warn "no ${LABEL}.tar.gz in backup - skipping (older archive?)"
    continue
  fi
  VOL="$(volume_of "${C}" "${DEST}")"
  if [ -z "${VOL}" ]; then
    warn "cannot resolve the ${LABEL} volume: container ${C} does not exist yet."
    warn "Run 'make up' once (creates volumes), then re-run this restore to load ${LABEL}."
    continue
  fi
  WAS_RUNNING=0
  if container_running "${C}"; then
    WAS_RUNNING=1
    log "stopping ${C} to restore its data volume..."
    docker stop "${C}" >/dev/null
  fi
  docker run --rm -v "${VOL}:/data" -v "${WORK}:/in:ro" alpine \
    sh -c "rm -rf /data/* /data/..?* /data/.[!.]* 2>/dev/null; tar -xzf /in/${LABEL}.tar.gz -C /data"
  ok "${LABEL} volume restored"
  if [ "${WAS_RUNNING}" -eq 1 ]; then
    docker start "${C}" >/dev/null
    log "${C} started again (Vault may need unsealing: make unseal)"
  fi
done

step "4/5  Restore MongoDB"
if [ ! -f "${WORK}/mongodb.archive.gz" ]; then
  warn "no mongodb.archive.gz in backup - skipping"
elif ! container_running tesa-mongodb; then
  warn "tesa-mongodb is not running - skipping the MongoDB load."
  warn "Bring the stack up (make up) and re-run this restore to load the dumps."
else
  docker exec -i tesa-mongodb sh -c \
    "mongorestore --quiet -u '${MROOT_USER}' -p '${MROOT_PASS}' --authenticationDatabase admin --archive --gzip --drop" \
    < "${WORK}/mongodb.archive.gz"
  ok "MongoDB restored"
fi

step "5/5  Restore TimescaleDB"
if [ ! -f "${WORK}/timescaledb.dump" ]; then
  warn "no timescaledb.dump in backup - skipping"
elif ! container_running tesa-timescaledb; then
  warn "tesa-timescaledb is not running - skipping the TimescaleDB load."
  warn "Bring the stack up (make up) and re-run this restore to load the dumps."
else
  docker exec -i tesa-timescaledb sh -c \
    "pg_restore -U '${PG_USER}' -d '${PG_DB}' --clean --if-exists --no-owner" \
    < "${WORK}/timescaledb.dump" || warn "pg_restore reported non-fatal warnings"
  ok "TimescaleDB restored"
fi

step "Done"
ok "Restore complete. Restart the stack:  make restart   (then check: make health)"
