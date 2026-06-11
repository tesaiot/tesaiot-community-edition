<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Configuration Reference

All runtime configuration lives in two places:

1. **`.env`** — secrets and per-deployment values (created from `.env.example`).
2. **`config/`** — service config files mounted read-only into containers.

The Community Edition follows a strict **config-in-environment** rule: nothing
sensitive is hardcoded in source or in `docker-compose.yml`. Every secret comes
from `.env`.

---

## 1. The `.env` file

Copy and fill it (or let `generate-secrets.sh` do it):

```bash
cp .env.example .env        # then edit, OR:
./scripts/generate-secrets.sh   # fills every CHANGEME_* with a random secret
```

`.env` is created with mode `600` and is git-ignored. **Never commit it.**

### 1.1 Deployment identity

| Variable | Default | Purpose |
|----------|---------|---------|
| `DOMAIN` | `localhost` | Public host the platform answers on. Used for TLS SANs and public URLs. |
| `DEFAULT_ORG_ID` | `default-org` | The single organization id. **Do not change after first boot** — it is written into stored data. |
| `TZ` | `Asia/Bangkok` | Container timezone. |
| `BUILD_TAG` / `CACHEBUST` / `BUILD_DATE` / `BUILD_HASH` | `latest` / `1` / `unknown` | Image tag + build metadata. |

> CE is **single-organization**. The `organization_id` columns/fields are kept
> in the schema so existing queries keep working, but the platform always reads
> and writes `DEFAULT_ORG_ID`.

### 1.2 HashiCorp Vault

| Variable | Set by | Purpose |
|----------|--------|---------|
| `VAULT_UNSEAL_KEY_1..3` | `init-vault-pki.sh` | Unseal key shares (3 shares, threshold 2). |
| `VAULT_ROOT_TOKEN` | `init-vault-pki.sh` | Root token. |
| `VAULT_PKI_PATH` | `pki-int` | Mount path of the issuing (intermediate) PKI engine. |

Leave the unseal keys blank for a fresh install; the init script fills them in.
**These are the most sensitive values in the file — back them up securely.**

### 1.3 MongoDB

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONGO_INITDB_ROOT_USERNAME` | `mongoadmin` | Root user (admin DB). |
| `MONGO_INITDB_ROOT_PASSWORD` | *(random)* | Root password. |
| `MONGO_INITDB_DATABASE` | `tesa_iot` | Application database name. |
| `MONGODB_USER` | `iot_user` | Application user the API connects as. |
| `MONGODB_PASSWORD` | *(random)* | Application user password. |
| `MONGODB_DATABASE` | `tesa_iot` | DB the API uses. |
| `MONGODB_AUTH_SOURCE` | `admin` | Auth database. |

### 1.4 TimescaleDB / PostgreSQL

| Variable | Default | Purpose |
|----------|---------|---------|
| `POSTGRES_USER` | `postgres` | DB superuser. |
| `POSTGRES_PASSWORD` | *(random)* | Password. |
| `POSTGRES_DB` | `tesa_telemetry` | Telemetry database. |

### 1.5 Redis

| Variable | Purpose |
|----------|---------|
| `REDIS_PASSWORD` | Password (cache + rate-limit storage). |

### 1.6 API / auth

| Variable | Default | Purpose |
|----------|---------|---------|
| `JWT_SECRET` | *(random, 48)* | HS256 JWT signing secret — must be long & random. |
| `SECRET_KEY` | *(random, 48)* | Flask secret key. |
| `BCRYPT_LOG_ROUNDS` | `12` | bcrypt cost factor (env-driven; never hardcoded). |
| `ADMIN_EMAIL` | `admin@localhost` | Bootstrap admin login. |
| `ADMIN_USERNAME` | `admin` | Bootstrap admin username. |
| `ADMIN_PASSWORD` | *(random, 20)* | Bootstrap admin password. |
| `ADMIN_BYPASS_RATE_LIMIT` | `true` | Let the bootstrap admin bypass per-IP login rate limiting. |
| `LOG_LEVEL` | `INFO` | API log level. |

### 1.7 Public-facing URLs

Advertised to devices (QR enrollment, telemetry ingest). Defaulted from `DOMAIN`.

| Variable | Default |
|----------|---------|
| `TESA_PUBLIC_API_BASE_URL` | `https://localhost` |
| `TESA_PUBLIC_INGEST_BASE_URL` | `https://localhost:9444` |
| `TESA_PUBLIC_MQTT_HOST` | `localhost` |
| `TESA_PUBLIC_MQTT_TLS_PORT` | `8884` (serverTLS) |
| `TESA_PUBLIC_MQTT_MTLS_PORT` | `8883` (mTLS) |
| `TESA_PUBLIC_MQTT_WS_PORT` | `8083` |

### 1.8 Email / OTP (optional)

Leave `EMAIL_ENABLED=false` to log mail to stdout instead of sending.

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMAIL_ENABLED` | `false` | Master switch. |
| `EMAIL_HOST` / `EMAIL_PORT` | `smtp.example.com` / `587` | SMTP server. |
| `EMAIL_USE_TLS` | `true` | STARTTLS. |
| `EMAIL_USER` / `EMAIL_PASSWORD` | empty | SMTP credentials. |
| `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME` | `noreply@localhost` / `TESAIoT Platform` | From header. |
| `EMAIL_PROVIDER` | `smtp` | `smtp` or `resend`. |
| `RESEND_API_KEY` | empty | If using Resend. |
| `OTP_LENGTH` / `OTP_EXPIRE_MINUTES` / `OTP_MAX_ATTEMPTS` / `OTP_COOLDOWN_SECONDS` | `6` / `15` / `3` / `30` | OTP policy. |

### 1.9 EMQX broker

| Variable | Purpose |
|----------|---------|
| `EMQX_DASHBOARD_PASSWORD` | Dashboard (`:18083`) admin password. |
| `EMQX_WEBHOOK_SECRET` | Shared bearer secret EMQX presents to the API auth/ACL webhooks. **Must match on both sides** (set automatically). |
| `EMQX_CERT_CN` | CN for the EMQX server cert issued by vault-agent (defaults to `DOMAIN`). |
| `EMQX_CERT_ALT_NAMES` | Comma-separated SANs (e.g. `localhost,mqtt.localhost`). |
| `EMQX_CERT_IP_SANS` | IP SANs (e.g. `127.0.0.1`). |

### 1.10 MQTT credentials

| Variable | Purpose |
|----------|---------|
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Broker internal user. |
| `MQTT_BRIDGE_PASSWORD` | Password for the internal `mqtt-bridge` service account (built-in auth DB). |
| `BRIDGE_API_USER` | API account the bridge logs in as to forward telemetry (defaults to the bootstrap admin). Must exist in the user registry. |
| `BRIDGE_API_PASSWORD` | Password for `BRIDGE_API_USER`. |

### 1.11 APISIX gateway

| Variable | Purpose |
|----------|---------|
| `APISIX_ADMIN_KEY` | Admin API key (provision routes/consumers). 32+ chars. |
| `APISIX_ADMIN_URL` | `http://tesa-apisix:9180/apisix/admin`. |

### 1.12 TLS material

The TLS directory is fixed at `./config/tls` (hardcoded in the
`docker-compose.yml` nginx mount — there is no env override). It holds
`server-cert.pem`, `server-key.pem`, `ca-bundle.pem`.

---

## 2. Config files in `config/`

These are mounted read-only into containers. A few carry `CHANGEME_*`
placeholders that `generate-secrets.sh` substitutes from `.env`.

> **Template vs rendered:** the five secret-bearing files below
> (`emqx.conf`, `auth-built-in-db-bootstrap.csv`, `config.yaml`, `apisix.yaml`,
> `30-iot-mtls.conf`) are **rendered** by `generate-secrets.sh` from the
> committed `*.tpl` templates next to them. Edit the `.tpl`, then re-render
> with `make secrets` — direct edits to the rendered file are overwritten on
> the next render, and the rendered files are `.gitignore`d because they
> contain live secrets.

| Path | Mounted into | Purpose |
|------|--------------|---------|
| `config/vault/vault-auto-unseal.hcl` | vault | Vault server config. |
| `config/vault-agent/vault-agent.hcl` + `templates/` + `scripts/` | vault-agent | Cert/token rendering + auto-rotation. |
| `config/vault-policies/api-csr-signing.hcl` | vault (loaded by init) | API PKI policy. |
| `config/mongodb/init-mongo.js` | mongodb | Creates app user, collections, default org. |
| `config/timescaledb/init-timescale.sql` | timescaledb | Telemetry hypertables + aggregates. |
| `config/emqx/emqx.conf` | emqx | Listeners (1883/8883/8884/8083/8084), auth/ACL webhooks. |
| `config/emqx/acl.conf` | emqx | Fallback ACL. |
| `config/emqx/auth-built-in-db-bootstrap.csv` | emqx | Seeds the `mqtt-bridge` user. |
| `config/nginx/nginx.conf` + `conf.d/*.conf` | nginx | serverTLS (`20-admin-api.conf`) + mTLS (`30-iot-mtls.conf`) + redirect (`10-redirect.conf`). |
| `config/apisix/config.yaml` | apisix | Gateway config + admin key. |
| `config/apisix/apisix.yaml` | apisix | Declarative routes, consumers, serverTLS cert. |
| `config/apisix/mtls-routes.yaml` | (reference) | Optional mTLS route patterns to merge in. |

Redis has **no** config file — it is configured entirely via command-line
flags in `docker-compose.yml` (the password comes from `.env`).

---

## 3. Changing the domain after install

The cleanest way is to set the domain on first install (`make install
DOMAIN=...`). To change it later:

```bash
make set-domain DOMAIN=iot.newcompany.com
make init-pki        # re-appends the Vault client-CA chain after the cert regen
```

`make set-domain` re-derives every `DOMAIN`-dependent var in `.env`
(`EMQX_CERT_*`, `TESA_PUBLIC_*`, `ADMIN_EMAIL`, `BRIDGE_API_USER`, the APISIX
SNI list), regenerates the bootstrap TLS cert for the new CN/SAN, and
recreates the services with `docker compose up -d` — a plain
`docker compose restart` would **not** re-read `.env`. Then re-issue any
Vault-PKI server certs for the new SANs (see
[certificate-lifecycle.md](certificate-lifecycle.md)).

> Do **not** change `DEFAULT_ORG_ID` after first boot.

---

## 4. Resource limits

`docker-compose.yml` sets memory/CPU limits per service (MongoDB & TimescaleDB
2 GB, API 2 GB, Redis 768 MB, etc.). Adjust the `deploy.resources` blocks to fit
your host, then `docker compose up -d` to apply.

---

## 5. Logging

All services use the JSON-file driver with rotation (`max-size: 10m`,
`max-file: 3`). The API also writes to the mounted `./logs/` directory. View
logs with `make logs` (all) or `make logs s=api` (one service).
