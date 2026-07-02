#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# reset-setup.sh - hand an installed instance back to the first-run setup
# wizard. The web-facing setup endpoints NEVER offer this: recovery requires
# host access (this script + the docker socket + .env), mirroring the industry
# recovery pattern (n8n user-management:reset, Nextcloud CAN_INSTALL).
#
# What it does (after an explicit typed confirmation):
#   1. deletes the human admin accounts (service accounts are kept),
#   2. clears the system_config 'setup' completion flag,
#   3. rotates SETUP_TOKEN in .env and blanks ADMIN_PASSWORD (so the env
#      seeder does not immediately re-create an admin from stale values),
#   4. recreates the api container so it picks up the new environment.
#
# Devices, telemetry, certificates and all other data are untouched.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

env_set() {  # key value   (same portable in-place edit as init-vault-pki.sh)
  local key="$1" val="$2"
  val="${val//\\/\\\\}"
  val="${val//|/\\|}"
  val="${val//&/\\&}"
  if grep -qE "^${key}=" "${ENV_FILE}"; then
    sed "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}" > "${ENV_FILE}.tmp" \
      && mv "${ENV_FILE}.tmp" "${ENV_FILE}"
  else
    printf "%s=%s\n" "${key}" "${val}" >> "${ENV_FILE}"
  fi
}

MONGO_C="tesa-mongodb"
API_C="tesa-api"

[ -f "${ENV_FILE}" ] || die ".env not found - nothing to reset"

MROOT_USER="$(env_get MONGO_INITDB_ROOT_USERNAME)"
MROOT_PASS="$(env_get MONGO_INITDB_ROOT_PASSWORD)"
MDB="$(env_get MONGODB_DATABASE 2>/dev/null || echo tesa_iot)"

docker inspect "${MONGO_C}" >/dev/null 2>&1 || die "${MONGO_C} is not running - start the stack first (make up)"

warn "This RESETS the platform to its first-run state:"
warn "  - human admin accounts are DELETED (devices/telemetry/certs are kept)"
warn "  - the setup wizard reopens, gated by a freshly rotated SETUP_TOKEN"
printf "Type RESET to continue: "
read -r CONFIRM
[ "${CONFIRM}" = "RESET" ] || die "aborted (nothing changed)"

step "1/4  Removing human admin accounts"
DELETED="$(docker exec "${MONGO_C}" mongosh --quiet \
  -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin "${MDB}" \
  --eval '
    const r = db.users.deleteMany({
      role: { $in: ["admin", "super_admin", "organization_admin", "org_admin", "platform_admin"] },
      is_service_account: { $ne: true },
    });
    print(r.deletedCount);
  ' | tail -1)"
ok "deleted ${DELETED} admin account(s)"

step "2/4  Clearing the setup-completed flag"
docker exec "${MONGO_C}" mongosh --quiet \
  -u "${MROOT_USER}" -p "${MROOT_PASS}" --authenticationDatabase admin "${MDB}" \
  --eval 'db.system_config.deleteOne({_id: "setup"});' >/dev/null
ok "setup flag cleared"

step "3/4  Rotating SETUP_TOKEN and blanking ADMIN_PASSWORD in .env"
NEW_TOKEN="$(gen_secret 48)"
env_set SETUP_TOKEN "${NEW_TOKEN}"
env_set ADMIN_PASSWORD ""
ok "SETUP_TOKEN rotated; ADMIN_PASSWORD blanked (env seeding disabled)"

step "4/4  Recreating the api container (picks up the new environment)"
compose up -d --force-recreate api >/dev/null
ok "api recreated"

DOMAIN_VAL="$(domain)"
cat <<EOF

  Setup wizard is OPEN again. Claim the instance at:

      https://${DOMAIN_VAL}/setup

  One-time setup token (also in .env as SETUP_TOKEN):

      ${NEW_TOKEN}

EOF
