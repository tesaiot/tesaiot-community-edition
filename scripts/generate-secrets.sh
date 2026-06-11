#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# generate-secrets.sh - create .env from .env.example with strong random
# secrets, generate the MongoDB keyfile, write a first-run self-signed
# CA + server certificate into ./config/tls so TLS works on boot before
# Vault PKI takes over, and render the secret-bearing config templates
# (config/**/*.tpl -> the mounted runtime files).
#
# Idempotent: existing .env / keyfile / certs are kept unless --force, but the
# *.tpl -> runtime-config render runs EVERY time, from the pristine committed
# template, so the rendered files always match the current .env (re-install
# after a purge can never silently keep stale secrets, and the git tree never
# carries live secrets - the rendered paths are in .gitignore).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

FORCE=0
DOMAIN_ARG=""
for arg in "$@"; do
  case "$arg" in
    "") ;;  # tolerate an empty (quoted) argument from wrappers
    --force) FORCE=1 ;;
    --domain=*) DOMAIN_ARG="${arg#--domain=}" ;;
    *) die "unknown arg: $arg (use --force, --domain=example.com)" ;;
  esac
done

command -v openssl >/dev/null 2>&1 || die "openssl is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required (used to patch the APISIX TLS material safely)"

# Validate --domain as an RFC-1123 hostname (labels of [A-Za-z0-9-], no
# leading/trailing hyphen, dot-separated, <=253 chars). Reject anything else
# with a clear error instead of seeding a broken value into certs and URLs.
if [ -n "${DOMAIN_ARG}" ]; then
  if [ "${#DOMAIN_ARG}" -gt 253 ] \
     || ! printf '%s' "${DOMAIN_ARG}" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$'; then
    die "invalid --domain '${DOMAIN_ARG}' - expected a hostname like iot.example.com (letters/digits/hyphens, dot-separated labels)"
  fi
fi

# Replace (or set) a single KEY=VALUE in .env. Defined at top level so both
# secret generation and the (idempotent) domain-wiring step can use it.
replace() {  # key  value
  local key="$1" val="$2"
  # Escape everything sed treats specially in the replacement text: backslash
  # FIRST (so we don't double-escape), then the | delimiter and &.
  val="${val//\\/\\\\}"
  val="${val//|/\\|}"
  val="${val//&/\\&}"
  # Portable in-place edit (BSD sed on macOS needs an arg for -i; GNU does
  # not) — write to a temp file and move it back so it works on both.
  sed "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}" > "${ENV_FILE}.tmp" \
    && mv "${ENV_FILE}.tmp" "${ENV_FILE}"
}

# Ensure KEY holds a real secret in .env: generate one if the key is missing,
# empty, or still a CHANGEME placeholder. Lets older .env files gain new keys
# (e.g. EMQX_NODE_COOKIE) without --force, and keeps re-renders deterministic.
ensure_env_secret() {  # key  nchars
  local key="$1" n="$2" cur
  cur="$(env_get "${key}" 2>/dev/null || true)"
  if [ -z "${cur}" ] || [[ "${cur}" == CHANGEME* ]]; then
    if grep -qE "^${key}=" "${ENV_FILE}"; then
      replace "${key}" "$(gen_secret "${n}")"
    else
      printf "%s=%s\n" "${key}" "$(gen_secret "${n}")" >> "${ENV_FILE}"
    fi
    ok "generated ${key}"
  fi
}

# Re-derive every user-facing host/origin/URL from a single DOMAIN. Safe to run
# on an existing .env, so "set the domain in one place" is literally true: the
# derived EMQX_CERT_*/TESA_PUBLIC_*/ADMIN_EMAIL/BRIDGE_API_USER vars are always
# rebuilt from DOMAIN, never left stale. Container-internal hosts and the
# nginx 'server_name _' are intentionally NOT touched here.
apply_domain() {  # domain
  local d="$1"
  replace DOMAIN "${d}"
  replace EMQX_CERT_CN "${d}"
  # Keep localhost as a SAN so on-box mqtt tooling (localhost:8883/8884) still
  # validates against the issued EMQX cert after a custom-domain install.
  # 'tesa-emqx' MUST stay so the in-cluster mqtt-bridge can do full hostname
  # verification (MQTT_TLS_VERIFY_HOSTNAME=true) over the internal Docker DNS.
  replace EMQX_CERT_ALT_NAMES "${d},mqtt.${d},localhost,tesa-emqx"
  replace TESA_PUBLIC_API_BASE_URL "https://${d}"
  replace TESA_PUBLIC_INGEST_BASE_URL "https://${d}:9444"
  replace TESA_PUBLIC_MQTT_HOST "${d}"
  # Public hostnames advertised in onboarding artefacts so a custom domain
  # propagates without hand-editing:
  #   TESA_MQTT_DOMAIN      -> MQTT host baked into device certificate bundles
  #   TESA_PROVISION_DOMAIN -> host in factory-registration QR URLs
  #   TESA_ADMIN_DOMAIN     -> host in account-setup / password-reset email links
  #   EMAIL_FROM_ADDRESS    -> From: of outgoing mail (also drives cert email_domain)
  replace TESA_MQTT_DOMAIN "${d}"
  replace TESA_PROVISION_DOMAIN "provision.${d}"
  replace TESA_ADMIN_DOMAIN "admin.${d}"
  replace EMAIL_FROM_ADDRESS "noreply@${d}"
  replace ADMIN_EMAIL "admin@${d}"
  # Least-privilege service account the bridge logs in with (the API
  # auto-creates it with telemetry-only permissions from BRIDGE_API_*).
  replace BRIDGE_API_USER "bridge@${d}"
}

# ---------------------------------------------------------------------------
step "1/4  .env"
# ---------------------------------------------------------------------------
if [ -f "${ENV_FILE}" ] && [ "${FORCE}" -eq 0 ]; then
  warn ".env already exists - keeping it (use --force to regenerate secrets)."
else
  [ -f "${ENV_EXAMPLE}" ] || die ".env.example missing"
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"

  # Replace every CHANGEME_* with a fresh random secret.
  replace VAULT_ROOT_TOKEN          "$(gen_secret 40)"
  replace MONGO_INITDB_ROOT_PASSWORD "$(gen_secret 32)"
  replace MONGODB_PASSWORD          "$(gen_secret 32)"
  replace POSTGRES_PASSWORD         "$(gen_secret 32)"
  replace REDIS_PASSWORD            "$(gen_secret 32)"
  replace JWT_SECRET                "$(gen_secret 48)"
  replace SECRET_KEY                "$(gen_secret 48)"
  replace ADMIN_PASSWORD            "$(gen_secret 20)"
  replace EMQX_DASHBOARD_PASSWORD   "$(gen_secret 24)"
  replace EMQX_WEBHOOK_SECRET       "$(gen_secret 32)"
  replace MQTT_PASSWORD             "$(gen_secret 24)"
  replace MQTT_BRIDGE_PASSWORD      "$(gen_secret 24)"
  replace APISIX_ADMIN_KEY          "$(gen_secret 32)"
  replace MTLS_GATEWAY_SECRET       "$(gen_secret 32)"
  # Least-privilege bridge service account: its OWN password, independent of
  # the admin password (the bridge must never hold admin credentials).
  replace BRIDGE_API_PASSWORD       "$(gen_secret 24)"

  # Domain wiring (initial creation). Re-derives all host/origin/URL vars.
  [ -n "${DOMAIN_ARG}" ] && apply_domain "${DOMAIN_ARG}"

  chmod 600 "${ENV_FILE}"
  ok ".env created with generated secrets (admin password saved in .env: ADMIN_PASSWORD)"
fi

# Secrets that are substituted into rendered config files and therefore must
# live in .env (re-renders stay deterministic). Also upgrades pre-existing
# .env files that predate these keys.
ensure_env_secret EMQX_NODE_COOKIE 32
ensure_env_secret APISIX_SAMPLE_DEVICE_API_KEY 32
ensure_env_secret BRIDGE_API_PASSWORD 24

# ---------------------------------------------------------------------------
# Idempotent domain re-wiring. Runs whenever --domain is supplied, even on an
# existing .env (independent of secret generation). This makes the custom-
# domain path — install once on localhost, then re-run with --domain=iot.acme.com
# — actually apply, instead of being silently skipped with the .env block above.
# ---------------------------------------------------------------------------
DOMAIN_CHANGED=0
if [ -n "${DOMAIN_ARG}" ] && [ -f "${ENV_FILE}" ]; then
  CUR_DOMAIN="$(env_get DOMAIN 2>/dev/null || true)"
  if [ "${CUR_DOMAIN}" != "${DOMAIN_ARG}" ]; then
    [ -n "${CUR_DOMAIN}" ] \
      && warn "Changing DOMAIN: '${CUR_DOMAIN}' -> '${DOMAIN_ARG}' (re-deriving EMQX_CERT_*/TESA_PUBLIC_*/ADMIN_EMAIL/BRIDGE_API_USER)."
    apply_domain "${DOMAIN_ARG}"
    DOMAIN_CHANGED=1
    ok "DOMAIN set to ${DOMAIN_ARG} (all derived host/origin/URL vars re-applied)."
  fi
fi

DOMAIN_VAL="$(domain)"
log "Using DOMAIN=${DOMAIN_VAL}"

# ---------------------------------------------------------------------------
step "2/4  MongoDB keyfile"
# ---------------------------------------------------------------------------
KEYFILE="${ROOT_DIR}/config/mongodb/mongodb-keyfile"
if [ -f "${KEYFILE}" ] && [ "${FORCE}" -eq 0 ]; then
  ok "keyfile already present - keeping it"
else
  openssl rand -base64 756 > "${KEYFILE}"
  chmod 400 "${KEYFILE}"
  # mongod runs as uid 999 in the official image; make it readable there.
  chown 999:999 "${KEYFILE}" 2>/dev/null || true
  ok "MongoDB keyfile generated (config/mongodb/mongodb-keyfile)"
fi

# ---------------------------------------------------------------------------
step "3/4  First-run TLS material (self-signed)"
# ---------------------------------------------------------------------------
TLS_DIR="${ROOT_DIR}/config/tls"
mkdir -p "${TLS_DIR}"
SRV_CERT="${TLS_DIR}/server-cert.pem"
SRV_KEY="${TLS_DIR}/server-key.pem"
CA_BUNDLE="${TLS_DIR}/ca-bundle.pem"

# A domain change implies a new cert: the bootstrap cert's CN/SAN carry the
# OLD domain, while the APISIX snis below are rewritten to the new one — that
# mismatch would make :9443 stop presenting the cert at all. So regenerate on
# --force OR whenever DOMAIN actually changed.
if [ -f "${SRV_CERT}" ] && [ "${FORCE}" -eq 0 ] && [ "${DOMAIN_CHANGED}" -eq 0 ]; then
  ok "server cert already present - keeping it (Vault PKI may replace it later)"
else
  TMP="$(mktemp -d)"
  trap 'rm -rf "${TMP}"' EXIT
  # Self-signed CA.
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "${TMP}/ca-key.pem" -out "${TMP}/ca.pem" -days 3650 \
    -subj "/O=TESAIoT Community Edition/CN=TESAIoT Community Edition Bootstrap CA" >/dev/null 2>&1
  # Server cert signed by that CA, SAN = DOMAIN (+localhost/127.0.0.1).
  openssl req -newkey rsa:2048 -nodes \
    -keyout "${SRV_KEY}" -out "${TMP}/server.csr" \
    -subj "/O=TESAIoT Community Edition/CN=${DOMAIN_VAL}" >/dev/null 2>&1
  cat > "${TMP}/ext.cnf" <<EOF
subjectAltName = DNS:${DOMAIN_VAL},DNS:localhost,DNS:mqtt.${DOMAIN_VAL},IP:127.0.0.1
EOF
  openssl x509 -req -in "${TMP}/server.csr" \
    -CA "${TMP}/ca.pem" -CAkey "${TMP}/ca-key.pem" -CAcreateserial \
    -out "${SRV_CERT}" -days 825 -extfile "${TMP}/ext.cnf" >/dev/null 2>&1
  # ca-bundle is the trust anchor nginx uses to verify client certs in mTLS.
  # init-vault-pki.sh APPENDS the Vault root+intermediate chain to it later
  # (that chain is what actually validates device certs).
  cp "${TMP}/ca.pem" "${CA_BUNDLE}"
  chmod 600 "${SRV_KEY}"
  chmod 644 "${SRV_CERT}" "${CA_BUNDLE}"
  ok "self-signed server cert + CA written to config/tls/"
  warn "These are bootstrap certs. Run init-vault-pki.sh (make init-pki) to switch to Vault-issued certs."
  [ "${DOMAIN_CHANGED}" -eq 1 ] \
    && warn "Domain changed: ca-bundle.pem was reset to the new bootstrap CA - re-run 'make init-pki' to re-append the Vault client-CA chain for device mTLS."
fi

# ---------------------------------------------------------------------------
step "4/4  Render secret-bearing config templates (*.tpl -> runtime files)"
# ---------------------------------------------------------------------------
# These config files are mounted into containers verbatim and need secrets
# baked in (EMQX/APISIX cannot take them via simple env overrides). The
# committed files are placeholder-only *.tpl templates; the rendered files
# live at the original (mounted) paths and are .gitignore'd. Rendering always
# starts from the pristine template, so it is idempotent and never leaves a
# stale secret behind.
WEBHOOK_SECRET="$(env_get EMQX_WEBHOOK_SECRET)"
DASH_PASS="$(env_get EMQX_DASHBOARD_PASSWORD)"
BRIDGE_PASS="$(env_get MQTT_BRIDGE_PASSWORD)"
APISIX_KEY="$(env_get APISIX_ADMIN_KEY)"
MTLS_GW_SECRET="$(env_get MTLS_GATEWAY_SECRET)"
EMQX_COOKIE="$(env_get EMQX_NODE_COOKIE)"
APISIX_SAMPLE_KEY="$(env_get APISIX_SAMPLE_DEVICE_API_KEY)"

render() {  # template  ->  rendered file (same path minus .tpl)
  local tpl="$1" dst="${1%.tpl}"
  [ -f "${tpl}" ] || die "template missing: ${tpl} (corrupted checkout?)"
  cp "${tpl}" "${dst}"
}

subst() {  # file  placeholder  value
  local file="$1" ph="$2" val="$3"
  [ -n "${val}" ] || die "empty value for ${ph} - is .env complete? (run generate-secrets.sh again)"
  # Same sed-escaping as replace(): backslash first, then | and &.
  val="${val//\\/\\\\}"
  val="${val//|/\\|}"
  val="${val//&/\\&}"
  # Portable in-place edit (works with both BSD and GNU sed).
  sed "s|${ph}|${val}|g" "${file}" > "${file}.tmp" && mv "${file}.tmp" "${file}"
}

# --- EMQX broker config + bootstrap auth CSV (read by uid 1000 in-container,
#     so the rendered files must stay group/other-readable) ---
EMQX_CONF="${ROOT_DIR}/config/emqx/emqx.conf"
render "${EMQX_CONF}.tpl"
subst "${EMQX_CONF}" "CHANGEME_WEBHOOK_SECRET"     "${WEBHOOK_SECRET}"
subst "${EMQX_CONF}" "CHANGEME_DASHBOARD_PASSWORD" "${DASH_PASS}"
subst "${EMQX_CONF}" "CHANGEME_EMQX_COOKIE"        "${EMQX_COOKIE}"
chmod 644 "${EMQX_CONF}"

EMQX_CSV="${ROOT_DIR}/config/emqx/auth-built-in-db-bootstrap.csv"
render "${EMQX_CSV}.tpl"
subst "${EMQX_CSV}" "CHANGEME_BRIDGE_MQTT_PASSWORD" "${BRIDGE_PASS}"
chmod 644 "${EMQX_CSV}"
ok "rendered config/emqx/{emqx.conf,auth-built-in-db-bootstrap.csv}"

# --- nginx mTLS terminator: the gateway marker the API requires (must equal
#     MTLS_GATEWAY_SECRET) before honouring any X-Client-* device header ---
MTLS_CONF="${ROOT_DIR}/config/nginx/conf.d/30-iot-mtls.conf"
render "${MTLS_CONF}.tpl"
subst "${MTLS_CONF}" "CHANGEME_MTLS_GATEWAY_SECRET" "${MTLS_GW_SECRET}"
chmod 600 "${MTLS_CONF}"   # nginx reads config as root; keep the marker off other host users
ok "rendered config/nginx/conf.d/30-iot-mtls.conf"

# --- APISIX runtime + declarative config (read by root in-container) ---
APISIX_CFG="${ROOT_DIR}/config/apisix/config.yaml"
render "${APISIX_CFG}.tpl"
subst "${APISIX_CFG}" "CHANGEME_APISIX_ADMIN_KEY" "${APISIX_KEY}"
chmod 600 "${APISIX_CFG}"

APISIX_YAML="${ROOT_DIR}/config/apisix/apisix.yaml"
render "${APISIX_YAML}.tpl"
subst "${APISIX_YAML}" "CHANGEME_DEVICE_API_KEY_SAMPLE" "${APISIX_SAMPLE_KEY}"
chmod 600 "${APISIX_YAML}"
ok "rendered config/apisix/{config.yaml,apisix.yaml}"

# APISIX serverTLS cert: inject the bootstrap server cert/key into the ssls
# block (replaces the multi-line PEM placeholders). Vault PKI can replace it
# later. Done in Python for safe YAML-block indentation. Runs every render,
# so the injected cert always matches the current config/tls material.
CERT_PEM="${SRV_CERT}" KEY_PEM="${SRV_KEY}" YAML="${APISIX_YAML}" python3 - <<'PY' && ok "patched apisix.yaml (serverTLS cert)"
import os
yaml = os.environ["YAML"]
def indent(path):
    with open(path) as f:
        return "".join("      " + line for line in f)  # 6-space block indent
cert = indent(os.environ["CERT_PEM"]).rstrip("\n")
key  = indent(os.environ["KEY_PEM"]).rstrip("\n")
with open(yaml) as f:
    text = f.read()
import re
# Replace the placeholder cert block (BEGIN..END CERTIFICATE) and key block.
text = re.sub(r"      -----BEGIN CERTIFICATE-----\n.*?-----END CERTIFICATE-----",
              cert, text, count=1, flags=re.S)
text = re.sub(r"      -----BEGIN PRIVATE KEY-----\n.*?-----END PRIVATE KEY-----",
              key, text, count=1, flags=re.S)
with open(yaml, "w") as f:
    f.write(text)
PY

# APISIX serverTLS SNI list: APISIX (standalone) only presents the cert above
# when the TLS SNI matches an entry in `snis`. nginx uses 'server_name _' so it
# matches any host, but APISIX needs DOMAIN explicitly or a handshake to :9443
# with SNI=<custom-domain> selects the wrong/default cert. Drive it from DOMAIN
# (keep localhost + mqtt.<domain> for on-box tooling). Done in Python so we only
# rewrite the snis block of ssl id:1, leaving the rest of the YAML untouched.
YAML="${APISIX_YAML}" DOMAIN_VAL="${DOMAIN_VAL}" python3 - <<'PY' && ok "patched apisix.yaml (serverTLS snis -> ${DOMAIN_VAL})"
import os, re
yaml_path = os.environ["YAML"]
d = os.environ["DOMAIN_VAL"]
# De-duplicate while preserving order; localhost always kept for on-box tooling.
names, seen = [], set()
for n in (d, f"mqtt.{d}", "localhost"):
    if n and n not in seen:
        seen.add(n); names.append(n)
block = "    snis:\n" + "".join(f'      - "{n}"\n' for n in names)
with open(yaml_path) as f:
    text = f.read()
# Replace the snis list (indented 4 spaces under ssls[].id) up to the next
# same-or-less-indented key (cert:). Non-greedy across the listed entries.
new, count = re.subn(
    r"    snis:\n(?:      - .*\n)+",
    block,
    text,
    count=1,
)
if count:
    with open(yaml_path, "w") as f:
        f.write(new)
PY

step "Done"
ok "Secrets ready. Next: ./scripts/install.sh   (or: make install)"
