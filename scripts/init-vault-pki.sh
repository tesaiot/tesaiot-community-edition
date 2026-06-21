#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# init-vault-pki.sh - initialise + unseal Vault, build the two-tier PKI
# hierarchy (pki-root -> pki-int), write the API policy + device/service
# roles, enable AppRole for the Vault Agent, and enable KV for device certs.
#
# Idempotent: re-running detects an already-initialised Vault and only
# (re)applies policies/roles. Unseal keys + root token are persisted to .env.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
require_env_file

VAULT_C=tesa-vault                       # container name
DOMAIN_VAL="$(domain)"
DEV_DOMAIN="${VAULT_PKI_DEVICE_DOMAIN:-device.tesa.local}"

vault_x() {  # token  args...
  local tok="$1"; shift
  docker exec -i -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="${tok}" "${VAULT_C}" vault "$@"
}

# Persist a key=value into .env (replace or append).
env_set() {  # key value
  local key="$1" val="$2"
  # Escape every character sed treats specially in the replacement text:
  # backslash FIRST (so we don't double-escape), then the | delimiter and &.
  val="${val//\\/\\\\}"
  val="${val//|/\\|}"
  val="${val//&/\\&}"
  if grep -qE "^${key}=" "${ENV_FILE}"; then
    # Portable in-place edit (works with both BSD/macOS and GNU sed).
    sed "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}" > "${ENV_FILE}.tmp" \
      && mv "${ENV_FILE}.tmp" "${ENV_FILE}"
  else
    printf "%s=%s\n" "${key}" "${val}" >> "${ENV_FILE}"
  fi
}

step "Waiting for Vault API"
for _ in $(seq 1 60); do
  if docker exec "${VAULT_C}" vault status >/dev/null 2>&1; then break; fi
  # status returns 2 when sealed - that still means the API is up.
  if docker exec "${VAULT_C}" sh -c 'wget -q -O- http://127.0.0.1:8200/v1/sys/health?uninitcode=200\&sealedcode=200 >/dev/null 2>&1'; then break; fi
  sleep 2
done

# ---------------------------------------------------------------------------
step "1/7  Initialise / unseal"
# ---------------------------------------------------------------------------
# Read vault status ONCE into a variable, then parse it. `vault status` exits 2
# when sealed/uninitialised, so piping it straight into grep under
# `set -o pipefail` would take the `|| echo` fallback and APPEND to grep's
# output (e.g. "true\ntrue"), corrupting the parsed value. Capturing first
# makes sealed/uninitialised parse deterministically.
STATUS_JSON="$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
  sh -c 'vault status -format=json 2>/dev/null' || true)"
INITED="$(printf '%s' "${STATUS_JSON}" | grep -o '"initialized":[^,]*' | cut -d: -f2 | tr -d ' ' || true)"
[ "${INITED}" = "true" ] || INITED=false

if [ "${INITED}" = "true" ]; then
  ok "Vault already initialised"
  ROOT_TOKEN="$(env_get VAULT_ROOT_TOKEN)"
  K1="$(env_get VAULT_UNSEAL_KEY_1)"; K2="$(env_get VAULT_UNSEAL_KEY_2)"; K3="$(env_get VAULT_UNSEAL_KEY_3)"
else
  log "Running vault operator init (3 key shares, threshold 2)"
  INIT_JSON="$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
    vault operator init -key-shares=3 -key-threshold=2 -format=json)"
  ROOT_TOKEN="$(printf '%s' "${INIT_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["root_token"])')"
  K1="$(printf '%s' "${INIT_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["unseal_keys_b64"][0])')"
  K2="$(printf '%s' "${INIT_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["unseal_keys_b64"][1])')"
  K3="$(printf '%s' "${INIT_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["unseal_keys_b64"][2])')"
  env_set VAULT_ROOT_TOKEN "${ROOT_TOKEN}"
  env_set VAULT_UNSEAL_KEY_1 "${K1}"
  env_set VAULT_UNSEAL_KEY_2 "${K2}"
  env_set VAULT_UNSEAL_KEY_3 "${K3}"
  ok "Vault initialised - unseal keys + root token saved to .env (KEEP SAFE)"
fi

# Unseal (no-op if already unsealed). Same capture-then-parse pattern as
# above: a sealed Vault exits 2, which must not corrupt the parsed value.
STATUS_JSON="$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 "${VAULT_C}" \
  sh -c 'vault status -format=json 2>/dev/null' || true)"
SEALED="$(printf '%s' "${STATUS_JSON}" | grep -o '"sealed":[^,]*' | cut -d: -f2 | tr -d ' ' || true)"
[ "${SEALED}" = "false" ] || SEALED=true   # fail-safe: unknown -> treat as sealed
if [ "${SEALED}" = "true" ]; then
  log "Unsealing"
  vault_x "" operator unseal "${K1}" >/dev/null
  vault_x "" operator unseal "${K2}" >/dev/null
  ok "Vault unsealed"
else
  ok "Vault already unsealed"
fi

TOK="${ROOT_TOKEN}"

# ---------------------------------------------------------------------------
step "2/7  PKI engines (pki-root + pki-int)"
# ---------------------------------------------------------------------------
if ! vault_x "${TOK}" secrets list -format=json | grep -q '"pki-root/"'; then
  vault_x "${TOK}" secrets enable -path=pki-root pki
  vault_x "${TOK}" secrets tune -max-lease-ttl=87600h pki-root
  vault_x "${TOK}" write -field=certificate pki-root/root/generate/internal \
    common_name="TESAIoT Community Edition Root CA" organization="TESAIoT Community Edition" \
    ttl=87600h key_type=rsa key_bits=4096 >/dev/null
  vault_x "${TOK}" write pki-root/config/urls \
    issuing_certificates="http://tesa-vault:8200/v1/pki-root/ca" \
    crl_distribution_points="http://tesa-vault:8200/v1/pki-root/crl" >/dev/null
  ok "Root PKI created"
else
  ok "Root PKI already present"
fi

if ! vault_x "${TOK}" secrets list -format=json | grep -q '"pki-int/"'; then
  vault_x "${TOK}" secrets enable -path=pki-int pki
  vault_x "${TOK}" secrets tune -max-lease-ttl=43800h pki-int
  CSR="$(vault_x "${TOK}" write -field=csr pki-int/intermediate/generate/internal \
    common_name="TESAIoT Community Edition Intermediate CA" organization="TESAIoT Community Edition" \
    key_type=rsa key_bits=4096)"
  SIGNED="$(echo "${CSR}" | vault_x "${TOK}" write -field=certificate pki-root/root/sign-intermediate \
    csr=- format=pem_bundle ttl=43800h)"
  echo "${SIGNED}" | vault_x "${TOK}" write pki-int/intermediate/set-signed certificate=- >/dev/null
  vault_x "${TOK}" write pki-int/config/urls \
    issuing_certificates="http://tesa-vault:8200/v1/pki-int/ca" \
    crl_distribution_points="http://tesa-vault:8200/v1/pki-int/crl" \
    ocsp_servers="http://tesa-vault:8200/v1/pki-int/ocsp" >/dev/null
  ok "Intermediate PKI created + signed by root"
else
  ok "Intermediate PKI already present"
fi

# Ensure the intermediate CRL is always fresh and auto-rebuilt so EMQX's
# enable_crl_check never fetches an expired CRL. Without auto_rebuild Vault's
# CRL expires (default 72h) and is only regenerated on the next revoke, which
# would make CRL validation fail-closed and block ALL devices. Idempotent.
vault_x "${TOK}" write pki-int/config/crl \
  expiry="72h" auto_rebuild=true auto_rebuild_grace_period="12h" \
  enable_delta=true delta_rebuild_interval="15m" >/dev/null 2>&1 \
  && ok "Intermediate CRL auto-rebuild enabled" \
  || ok "Intermediate CRL config skipped (older Vault?)"

# ---------------------------------------------------------------------------
step "3/7  PKI roles"
# ---------------------------------------------------------------------------
DEV_DOMAINS="${DEV_DOMAIN},*.${DEV_DOMAIN},${DOMAIN_VAL},localhost"

# Device certs (mTLS) - ECC, client auth.
vault_x "${TOK}" write pki-int/roles/iot-device-ecc \
  allowed_domains="${DEV_DOMAINS}" allow_subdomains=true allow_any_name=true \
  enforce_hostnames=false key_type=ec key_bits=256 \
  client_flag=true server_flag=false max_ttl=8760h ttl=8760h >/dev/null
# Generic device-cert sign role.
vault_x "${TOK}" write pki-int/roles/device-cert \
  allowed_domains="${DEV_DOMAINS}" allow_subdomains=true allow_any_name=true \
  enforce_hostnames=false key_type=any \
  client_flag=true server_flag=false max_ttl=8760h ttl=720h >/dev/null
# CSR signing role (devices submit their own CSR, arbitrary CN/email).
vault_x "${TOK}" write pki-int/roles/csr-signing \
  allow_any_name=true enforce_hostnames=false allow_ip_sans=true key_type=any \
  client_flag=true server_flag=true max_ttl=26280h ttl=8760h \
  use_csr_common_name=true use_csr_sans=true >/dev/null
# EMQX server cert (RSA + ECDSA), server+client auth.
for kt in "emqx-server rsa 2048" "emqx-server-ecdsa ec 256"; do
  set -- $kt
  vault_x "${TOK}" write "pki-int/roles/$1" \
    allowed_domains="${DOMAIN_VAL},localhost,*.${DOMAIN_VAL},mqtt.${DOMAIN_VAL}" \
    allow_subdomains=true allow_any_name=true enforce_hostnames=false allow_ip_sans=true \
    key_type="$2" key_bits="$3" server_flag=true client_flag=true \
    max_ttl=8760h ttl=2160h >/dev/null
done
# Platform service certs (nginx / apisix / mqtt-bridge).
vault_x "${TOK}" write pki-int/roles/platform-service \
  allow_any_name=true enforce_hostnames=false allow_ip_sans=true \
  key_type=rsa key_bits=2048 server_flag=true client_flag=true \
  max_ttl=8760h ttl=2160h >/dev/null
ok "Roles: iot-device-ecc, device-cert, csr-signing, emqx-server(+ecdsa), platform-service"

# ---------------------------------------------------------------------------
step "4/7  KV v2 for device cert storage"
# ---------------------------------------------------------------------------
if ! vault_x "${TOK}" secrets list -format=json | grep -q '"secret/"'; then
  vault_x "${TOK}" secrets enable -path=secret -version=2 kv >/dev/null
  ok "KV v2 enabled at secret/"
else
  ok "KV v2 already present"
fi

# ---------------------------------------------------------------------------
step "5/7  API policy"
# ---------------------------------------------------------------------------
docker cp "${ROOT_DIR}/config/vault-policies/api-csr-signing.hcl" \
  "${VAULT_C}:/tmp/api-pki.hcl"
vault_x "${TOK}" policy write api-pki /tmp/api-pki.hcl >/dev/null
ok "Policy 'api-pki' written"

# ---------------------------------------------------------------------------
step "6/7  AppRole for the Vault Agent"
# ---------------------------------------------------------------------------
if ! vault_x "${TOK}" auth list -format=json | grep -q '"approle/"'; then
  vault_x "${TOK}" auth enable approle >/dev/null
fi
vault_x "${TOK}" write auth/approle/role/api-service \
  token_policies="api-pki" token_ttl=1h token_max_ttl=24h \
  secret_id_ttl=0 token_num_uses=0 >/dev/null
ROLE_ID="$(vault_x "${TOK}" read -field=role_id auth/approle/role/api-service/role-id)"
SECRET_ID="$(vault_x "${TOK}" write -f -field=secret_id auth/approle/role/api-service/secret-id)"
printf "%s" "${ROLE_ID}"   > "${ROOT_DIR}/config/vault-agent/secrets-unified/role-id"
printf "%s" "${SECRET_ID}" > "${ROOT_DIR}/config/vault-agent/secrets-unified/secret-id"
chmod 600 "${ROOT_DIR}/config/vault-agent/secrets-unified/role-id" \
          "${ROOT_DIR}/config/vault-agent/secrets-unified/secret-id"
# Also persist the AppRole credentials to .env so docker-compose can inject them
# into the api as API_ROLE_ID / API_SECRET_ID. The api validates these at boot
# (Config.PRODUCTION_REQUIRED_SECRETS); without them the api worker refuses to
# start. The Vault Agent still reads the role-id/secret-id files above.
env_set API_ROLE_ID   "${ROLE_ID}"
env_set API_SECRET_ID "${SECRET_ID}"
ok "AppRole 'api-service' created; role-id/secret-id written for vault-agent + .env"

# ---------------------------------------------------------------------------
step "7/7  Client-CA bundle for the nginx mTLS terminator"
# ---------------------------------------------------------------------------
# nginx (config/nginx/conf.d/30-iot-mtls.conf) verifies device client certs
# against /etc/nginx/certs/ca-bundle.pem (bind-mounted from config/tls/).
# generate-secrets.sh seeds that file with the BOOTSTRAP self-signed CA only,
# which can never have issued a device cert - so without this step every
# Vault-issued device cert is rejected at the TLS handshake. Append the Vault
# root + intermediate chain (idempotent: skip if already present) and keep the
# bootstrap CA so anything still chained to it stays valid.
CA_BUNDLE="${ROOT_DIR}/config/tls/ca-bundle.pem"
mkdir -p "${ROOT_DIR}/config/tls"
VAULT_CHAIN="$(docker exec "${VAULT_C}" \
  wget -q -O- http://127.0.0.1:8200/v1/pki-int/ca_chain 2>/dev/null || true)"
if [ -z "${VAULT_CHAIN}" ]; then
  warn "Could not fetch pki-int/ca_chain from Vault - nginx mTLS will keep rejecting Vault-issued device certs until you re-run this script."
else
  FPR="$(printf '%s' "${VAULT_CHAIN}" | head -2 | tail -1)"   # 1st b64 line of the chain = cheap idempotency marker
  if [ -f "${CA_BUNDLE}" ] && grep -qF "${FPR}" "${CA_BUNDLE}"; then
    ok "Vault CA chain already present in config/tls/ca-bundle.pem"
  else
    printf '%s\n' "${VAULT_CHAIN}" >> "${CA_BUNDLE}"
    chmod 644 "${CA_BUNDLE}"
    ok "Vault root+intermediate CA chain appended to config/tls/ca-bundle.pem"
  fi
  # Reload nginx if it is already running (during install.sh it is not up yet;
  # it will read the updated bundle when it starts - both paths are fine).
  docker exec tesa-nginx nginx -s reload >/dev/null 2>&1 \
    && ok "nginx reloaded with the new client-CA bundle" \
    || log "nginx not running yet - it will pick the bundle up on start"
fi

step "Done"
ok "Vault PKI ready. Restart vault-agent so it picks up the new AppRole:"
echo "    docker compose restart vault-agent emqx api"
