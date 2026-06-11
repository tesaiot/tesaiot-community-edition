#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - EMQX certificate reload hook
#
# Triggers EMQX to pick up freshly issued certificates. EMQX 5.x applies new
# certs when a TLS listener (re)starts, so this restarts the TLS listeners via
# the management API. Best-effort: on any failure EMQX simply keeps serving the
# old cert until its next restart, which is safe (the cert is rotated ~30 days
# before expiry by the auto-rotate loop).
#
# IMPORTANT (toolbox): this runs inside the hashicorp/vault image (vault-agent
# container) which has NO curl and NO openssl — busybox wget only. It reaches
# EMQX over the Docker network at tesa-emqx:18083 (NOT localhost: that would
# be the agent container itself). EMQX_DASHBOARD_PASSWORD is passed through
# docker-compose from .env; if it is absent we skip quietly.

set -u

EMQX_DASHBOARD_URL="${EMQX_DASHBOARD_URL:-http://tesa-emqx:18083}"
EMQX_DASHBOARD_USER="${EMQX_DASHBOARD_USER:-admin}"
EMQX_DASHBOARD_PASSWORD="${EMQX_DASHBOARD_PASSWORD:-}"

echo "[$(date)] Reloading EMQX TLS listeners..."

if [ -z "${EMQX_DASHBOARD_PASSWORD}" ]; then
    echo "[$(date)] EMQX_DASHBOARD_PASSWORD not set - skipping API reload; EMQX will use new certs on next restart"
    exit 0
fi

# EMQX 5 management API wants a bearer token from /api/v5/login.
TOKEN="$(wget -q -O- \
    --header='Content-Type: application/json' \
    --post-data="{\"username\":\"${EMQX_DASHBOARD_USER}\",\"password\":\"${EMQX_DASHBOARD_PASSWORD}\"}" \
    "${EMQX_DASHBOARD_URL}/api/v5/login" 2>/dev/null \
  | sed -n 's/.*"token" *: *"\([^"]*\)".*/\1/p')"

if [ -z "${TOKEN}" ]; then
    echo "[$(date)] Warning: EMQX login failed; EMQX will use new certs on next restart" >&2
    exit 0
fi

# Restart each TLS listener so it re-reads cert/key/CA from disk. Existing
# connections on that listener reconnect (devices retry by design).
for lid in "ssl:mtls" "ssl:servertls" "wss:default"; do
    if wget -q -O /dev/null \
         --header="Authorization: Bearer ${TOKEN}" \
         --post-data='' \
         "${EMQX_DASHBOARD_URL}/api/v5/listeners/${lid}/restart" 2>/dev/null; then
        echo "[$(date)] listener ${lid} restarted"
    else
        echo "[$(date)] Warning: could not restart listener ${lid} (it will pick up certs on next restart)" >&2
    fi
done

echo "[$(date)] Certificate reload completed"
