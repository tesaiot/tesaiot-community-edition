#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# init-databases.sh - one-time database bootstrap:
#   - MongoDB: initiate the single-node replica set (rs0). The app user,
#     default org and collections are created by init-mongo.js on first boot.
#   - TimescaleDB: init-timescale.sql is applied automatically by the image
#     entrypoint on first boot; here we just verify the hypertable exists.
# Idempotent.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

MONGO_C=tesa-mongodb
PG_C=tesa-timescaledb
MROOT_USER="$(env_get MONGO_INITDB_ROOT_USERNAME)"
MROOT_PASS="$(env_get MONGO_INITDB_ROOT_PASSWORD)"
PG_USER="$(env_get POSTGRES_USER)"; PG_USER="${PG_USER:-postgres}"
PG_DB="$(env_get POSTGRES_DB)"; PG_DB="${PG_DB:-tesa_telemetry}"

# ---------------------------------------------------------------------------
step "1/2  MongoDB replica set"
# ---------------------------------------------------------------------------
log "Waiting for mongod"
for _ in $(seq 1 60); do
  if docker exec "${MONGO_C}" mongosh --quiet --eval 'db.runCommand({ping:1}).ok' \
       -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin >/dev/null 2>&1; then
    break
  fi
  # Before rs.initiate the auth may not be ready; also try unauthenticated ping.
  docker exec "${MONGO_C}" mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1 && break
  sleep 2
done

RS_OK="$(docker exec "${MONGO_C}" mongosh --quiet \
  -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin \
  --eval 'try { rs.status().ok } catch(e) { 0 }' 2>/dev/null || echo 0)"
RS_OK="$(echo "${RS_OK}" | tr -d '[:space:]')"

if [ "${RS_OK}" = "1" ]; then
  ok "Replica set rs0 already initiated"
else
  log "Initiating replica set rs0"
  docker exec "${MONGO_C}" mongosh --quiet \
    -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin \
    --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})' >/dev/null 2>&1 \
    || docker exec "${MONGO_C}" mongosh --quiet \
         --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})' >/dev/null 2>&1 || true
  # Wait until PRIMARY.
  for _ in $(seq 1 30); do
    STATE="$(docker exec "${MONGO_C}" mongosh --quiet \
      -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin \
      --eval 'try{rs.status().myState}catch(e){0}' 2>/dev/null | tr -d '[:space:]')"
    [ "${STATE}" = "1" ] && break
    sleep 2
  done
  ok "Replica set rs0 initiated (node is PRIMARY)"
fi

# ---------------------------------------------------------------------------
step "2/2  TimescaleDB hypertable"
# ---------------------------------------------------------------------------
log "Waiting for PostgreSQL"
for _ in $(seq 1 60); do
  docker exec "${PG_C}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null 2>&1 && break
  sleep 2
done

HT="$(docker exec "${PG_C}" psql -U "${PG_USER}" -d "${PG_DB}" -tAc \
  "SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name='device_telemetry';" 2>/dev/null | tr -d '[:space:]' || echo 0)"
if [ "${HT}" = "1" ]; then
  ok "device_telemetry hypertable present"
else
  warn "device_telemetry hypertable not found - re-applying init-timescale.sql"
  docker exec -i "${PG_C}" psql -U "${PG_USER}" -d "${PG_DB}" \
    < "${ROOT_DIR}/config/timescaledb/init-timescale.sql" >/dev/null 2>&1 || \
    warn "manual apply failed (may already be partially applied) - check 'make logs'"
fi

step "Done"
ok "Databases initialised."
