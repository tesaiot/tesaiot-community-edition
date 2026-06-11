#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition — EMQX Vault Agent wrapper with auto-rotation,
# pragmatic Vault self-unseal, and token-sink permission hardening.
#
# IMPORTANT (toolbox): this runs inside the hashicorp/vault image, which has
# NO openssl and NO curl. Everything below uses only binaries that exist
# there: busybox sh/wget/date/stat/grep/sleep + the vault CLI.

set -eu

CERT_PATH="/opt/emqx/etc/certs/cert-with-chain.pem"
TOKEN_SINK="/vault/token/api-token"
AGENT_CFG="/vault/config.hcl"
VAULT_ADDR="${VAULT_ADDR:-http://tesa-vault:8200}"

# Re-render when the rendered cert FILE is older than CERT_MAX_AGE_SECS.
# (No openssl in this image, so we can't read notAfter; file age is a sound
# proxy because the agent writes the file at issuance time. The emqx-server
# role issues 2160h (90 day) certs, so the 60-day default leaves a 30-day
# safety margin. Override via env.)
CERT_MAX_AGE_SECS=${CERT_MAX_AGE_SECS:-5184000}
# Cert-age check interval (default: 6 hours)
SLEEP_SECS=${SLEEP_SECS:-21600}
# Seal-status check interval (default: 30s — a sealed Vault stalls everything)
UNSEAL_CHECK_SECS=${UNSEAL_CHECK_SECS:-30}
# Token-sink permission fix interval (default: 30s)
TOKEN_PERMS_SECS=${TOKEN_PERMS_SECS:-30}

# ---------------------------------------------------------------------------
# Pragmatic Vault self-unseal (opt-out by leaving VAULT_UNSEAL_KEYS empty).
#
# TRADE-OFF, documented deliberately: after a host reboot Vault comes back
# SEALED and the whole platform stalls. The Shamir unseal keys already live in
# .env ON THE SAME HOST, so posting them from this side-car does not weaken
# the existing threat model — anyone who can read .env can unseal anyway. It
# trades "operator must run make unseal after every reboot" for availability.
# The production-grade alternative remains a cloud-KMS auto-unseal stanza in
# config/vault/vault-auto-unseal.hcl (see the commented seal "awskms" block)
# plus split custody of the Shamir keys. To opt out of self-unseal, leave the
# VAULT_UNSEAL_KEY_* vars empty/unset in .env.
# ---------------------------------------------------------------------------
unseal_loop() {
  while true; do
    # Treat a comma-only value as empty: compose renders
    # "${VAULT_UNSEAL_KEY_1:-},${VAULT_UNSEAL_KEY_2:-}" as just "," when the
    # shares are unset (the opt-out case).
    if [ -n "$(printf '%s' "${VAULT_UNSEAL_KEYS:-}" | tr -d ', ')" ]; then
      # /v1/sys/seal-status always answers 200, sealed or not.
      STATUS="$(wget -q -O- "${VAULT_ADDR}/v1/sys/seal-status" 2>/dev/null || true)"
      if printf '%s' "${STATUS}" | grep -q '"sealed":true'; then
        echo "[auto-unseal] Vault is sealed - submitting unseal keys..."
        OLD_IFS=$IFS; IFS=','
        for k in ${VAULT_UNSEAL_KEYS}; do
          [ -n "$k" ] || continue
          wget -q -O- --header='Content-Type: application/json' \
            --post-data="{\"key\":\"$k\"}" \
            "${VAULT_ADDR}/v1/sys/unseal" >/dev/null 2>&1 || true
        done
        IFS=$OLD_IFS
        STATUS="$(wget -q -O- "${VAULT_ADDR}/v1/sys/seal-status" 2>/dev/null || true)"
        if printf '%s' "${STATUS}" | grep -q '"sealed":false'; then
          echo "[auto-unseal] Vault unsealed."
        else
          echo "[auto-unseal] Vault still sealed (need more key shares? check VAULT_UNSEAL_KEYS)." >&2
        fi
      fi
    fi
    sleep "${UNSEAL_CHECK_SECS}"
  done
}

# ---------------------------------------------------------------------------
# Token-sink permission hardening. The agent's file sink rewrites the token
# 0640 root:root on every re-auth; the api container reads it as uid 1000.
# Re-assert owner/mode in a tight loop so the api never loses access for long
# and the token is never world-readable on the host bind-mount (see D9 note
# in config/vault-agent/vault-agent.hcl).
# ---------------------------------------------------------------------------
token_perms_loop() {
  while true; do
    for f in "${TOKEN_SINK}" "${TOKEN_SINK}-info.json"; do
      if [ -f "$f" ]; then
        chown 1000:1000 "$f" 2>/dev/null || true
        chmod 0440 "$f" 2>/dev/null || true
      fi
    done
    sleep "${TOKEN_PERMS_SECS}"
  done
}

# ---------------------------------------------------------------------------
# Certificate auto-rotation (file-age based; no openssl in this image).
# ---------------------------------------------------------------------------
auto_rotate_loop() {
  while true; do
    if [ -f "$CERT_PATH" ]; then
      NOW="$(date +%s)"
      MTIME="$(stat -c %Y "$CERT_PATH" 2>/dev/null || echo "$NOW")"
      AGE=$(( NOW - MTIME ))
      if [ "$AGE" -ge "$CERT_MAX_AGE_SECS" ]; then
        echo "[auto-rotate] Rendered cert is ${AGE}s old (limit ${CERT_MAX_AGE_SECS}s). Forcing re-render via vault agent -once..."
        # Re-render templates once (uses AppRole in config.hcl). Safe to run alongside main agent.
        vault agent -once -config="$AGENT_CFG" || true
        # reload-emqx.sh is also executed by the template 'command' on render; run once more as best-effort
        if [ -f /vault/scripts/reload-emqx.sh ]; then
          sh /vault/scripts/reload-emqx.sh || true
        fi
        echo "[auto-rotate] Re-render complete (new cert file written $(date))."
      fi
    fi
    sleep "$SLEEP_SECS"
  done
}

# Start background loops
unseal_loop &
token_perms_loop &
auto_rotate_loop &

# Exec main vault agent in foreground (PID 1)
exec vault agent -config="$AGENT_CFG"
