#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# init-emqx.sh - provision the internal mqtt-bridge user in EMQX's built-in
# authentication database using the password from .env. EMQX handles device
# and user auth via the API webhook (configured in emqx.conf); only the
# internal bridge account lives in the built-in DB.
# Idempotent: re-running just updates the password.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

EMQX_C=tesa-emqx
BRIDGE_PASS="$(env_get MQTT_BRIDGE_PASSWORD)"
[ -n "${BRIDGE_PASS}" ] || die "MQTT_BRIDGE_PASSWORD not set in .env"

step "Waiting for EMQX"
for _ in $(seq 1 60); do
  docker exec "${EMQX_C}" emqx ctl status >/dev/null 2>&1 && break
  sleep 2
done

step "Provisioning internal 'mqtt-bridge' user (built-in auth DB)"
# The built-in_database authenticator id is the password_based:built_in_database
# authenticator from emqx.conf. emqx ctl manages users on it.
if docker exec "${EMQX_C}" emqx ctl authn list >/dev/null 2>&1; then
  # Create (or overwrite) the bridge user. Try update first, then add.
  if docker exec "${EMQX_C}" emqx ctl authn-users \
        "password_based:built_in_database" add mqtt-bridge "${BRIDGE_PASS}" >/dev/null 2>&1; then
    ok "mqtt-bridge user created"
  elif docker exec "${EMQX_C}" emqx ctl authn-users \
        "password_based:built_in_database" update mqtt-bridge "${BRIDGE_PASS}" >/dev/null 2>&1; then
    ok "mqtt-bridge user password updated"
  else
    warn "Could not manage the user via 'emqx ctl authn-users'."
    warn "The user is also bootstrapped from auth-built-in-db-bootstrap.csv on first boot."
    warn "Ensure that CSV's password matches MQTT_BRIDGE_PASSWORD, or set it in the EMQX dashboard (:18083)."
  fi
else
  warn "authn not ready yet - the bootstrap CSV seeds mqtt-bridge on first boot."
fi

step "Done"
ok "EMQX broker auth provisioned. Device/user auth is served by the API webhook."
