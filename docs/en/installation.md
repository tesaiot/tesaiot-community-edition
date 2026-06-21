<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Installation Guide

This guide takes you from a bare Linux host to a fully running TESAIoT Platform
CE, with verification of every service. There are two paths:

- **Automated** — `make install` (recommended for first-time installs).
- **Manual** — run each step yourself for full control or debugging.

Both produce the same result.

---

## 0. Use your own domain (single source of truth)

If you are deploying on a real hostname (e.g. `iot.yourcompany.com`) instead of
`localhost`, set it **once** with the `--domain` flag — do **not** hand-edit
config files:

```bash
./scripts/generate-secrets.sh --domain=iot.yourcompany.com
make install
```

(or in one step: `make install DOMAIN=iot.yourcompany.com`)

`DOMAIN` in `.env` is the **single source of truth** for the public hostname.
The `--domain` flag wires it into `.env` and re-derives everything that is
host-dependent, so it propagates everywhere without editing many files:

- the **TLS certificate CN/SAN** (first-run self-signed cert, and later the
  Vault-PKI / EMQX certs — `EMQX_CERT_CN`, `EMQX_CERT_ALT_NAMES`);
- the **public API / ingest / MQTT URLs** advertised to devices
  (`TESA_PUBLIC_API_BASE_URL`, `TESA_PUBLIC_INGEST_BASE_URL`,
  `TESA_PUBLIC_MQTT_HOST`);
- the **onboarding hostnames** baked into device bundles, QR enrolment URLs and
  email links (`TESA_MQTT_DOMAIN`, `TESA_PROVISION_DOMAIN`, `TESA_ADMIN_DOMAIN`,
  `ADMIN_EMAIL`, `EMAIL_FROM_ADDRESS`, the APISIX TLS SNI list).

nginx uses `server_name _` so it answers on **any** host — there is nothing to
change there.

It is **idempotent and safe to re-run**: you can install on `localhost` first
and later run `make set-domain DOMAIN=iot.yourcompany.com` to switch — the
derived vars are always rebuilt from `DOMAIN`, never left stale, and the
bootstrap TLS certificate is regenerated for the new CN/SAN. `make set-domain`
applies the change with `docker compose up -d` (recreate) — a plain
`docker compose restart` would **not** re-read `.env`. If Vault PKI is already
initialised, finish with `make init-pki` so the Vault client-CA chain is
re-appended to the regenerated `ca-bundle.pem`.

> **DNS prerequisite:** before going live, create a DNS **A-record** (or AAAA)
> for your domain pointing at this host's public IP. Devices and browsers must
> resolve `iot.yourcompany.com` to the server for TLS and MQTT to work.

The rest of this guide uses `localhost`; substitute your domain wherever it
appears.

---

## 1. Prerequisites

### 1.1 Operating system

A 64-bit Linux host (Ubuntu 22.04 / 24.04 LTS or Debian 12 recommended).
The stack also runs on other distributions and on a Linux VM under macOS or
Windows, as long as Docker Engine and the Compose v2 plugin are available.

### 1.2 Required software

| Tool | Why | Check |
|------|-----|-------|
| **Docker Engine** | runs all 11 containers | `docker --version` |
| **Docker Compose v2 plugin** | orchestration (the legacy `docker-compose` is **not** supported) | `docker compose version` |
| **openssl** | generates secrets, keyfile, first-run TLS | `openssl version` |
| **python3** | patches the APISIX TLS material + SNI list during secret generation | `python3 --version` |
| **curl** | health checks, API probing | `curl --version` |
| **git** | clone the repo | `git --version` |
| **make** | runs the Makefile targets (optional but convenient) | `make --version` |

The `preflight-check.sh` script verifies all of these before installing.

### 1.3 Server sizing

| Profile | vCPU | RAM | Disk | Suitable for |
|---------|------|-----|------|--------------|
| Minimum | 2 | 4 GB | 20 GB | Evaluation, a handful of devices |
| Recommended | 4 | 8 GB | 50 GB SSD | Production, hundreds of devices |
| Comfortable | 8 | 16 GB | 100+ GB SSD | Thousands of devices / high telemetry rate |

The Compose file sets per-container memory/CPU limits (MongoDB and TimescaleDB
are capped at 2 GB each, the API at 2 GB). On a 4 GB host the stack runs but
leaves little headroom — 8 GB is the comfortable floor for production.
Preflight warns if less than **10 GB** of disk is free.

### 1.4 Host ports

The stack binds these host TCP ports. Make sure they are free (preflight warns
if any are already in use):

```
80    443   1883  8083  8084  8200  8883
8884  9080  9180  9443  9444  18083
```

(The API `:5566` and MongoDB `:27017` are **not** published on the host at
all — they are reachable only on the internal Docker network.)

If you run a firewall (UFW, firewalld, cloud security group), open at least
`443` (Admin UI / API), `9444` (mTLS ingest), and the MQTT ports your devices
use (`8883` mTLS and/or `8884` serverTLS). The management/plaintext ports
(`8200` Vault, `9080`/`9180` APISIX, `1883`/`8083`/`18083` EMQX) are published
on **loopback only** and never face the LAN.

### 1.5 Running on macOS / Windows (Docker Desktop)

The stack is cross-platform and runs on **Docker Desktop** (macOS — Intel and
Apple Silicon — and Windows with WSL 2). All images are multi-arch, so Apple
Silicon (arm64) pulls native images automatically. A few Docker-Desktop notes:

- **Allocate enough memory.** Docker Desktop → **Settings → Resources → Memory**
  must be **at least 6 GB (8 GB recommended)** for the 11 services. The default
  (often 2–4 GB) is not enough and MongoDB/TimescaleDB may be OOM-killed.
- **The known Desktop gotchas are already handled in the distribution** — you do
  *not* need any manual workaround:
  - The MongoDB replica-set keyfile is copied into the container and its
    permissions are fixed there at start-up, so the
    *"permissions on the keyfile are too open"* error that bind-mounted keyfiles
    cause on macOS/Windows does **not** happen here.
  - All shell scripts are written to run under both GNU (Linux) and BSD (macOS)
    tools and under the older **bash 3.2** that ships with macOS — run them with
    `bash scripts/<name>.sh` (or just use `make`).
- **`make`** is preinstalled on macOS (via Xcode Command Line Tools) and
  available on Windows through WSL/Git Bash; otherwise call the scripts directly.
- Everything else is identical to Linux. From here, skip to
  [section 4 (Get the code)](#4-get-the-code) — Docker Desktop already provides
  the Docker Engine + Compose v2, so you can ignore section 2.

---

## 2. Install Docker

If Docker is not already installed (skip if `docker compose version` works):

```bash
# Install Docker Engine + Compose plugin (official convenience script)
curl -fsSL https://get.docker.com | sudo sh

# Run docker without sudo (log out / back in afterwards)
sudo usermod -aG docker "$USER"

# Verify
docker --version
docker compose version
```

---

## 3. Clone the repository

```bash
git clone <your-fork-url> tesaiot-community-edition
cd tesaiot-community-edition
```

All commands below are run from the `tesaiot-community-edition/` directory.

---

## 4. Path A — Automated install (recommended)

```bash
# Fast path — pull the pre-built, multi-arch (amd64/arm64) images from GHCR:
make install PREBUILT=1

# OR build everything from source (contributors, customizing, or air-gapped):
make install

# Bind to a real domain on first run (recommended for production; either path):
make install PREBUILT=1 DOMAIN=iot.example.com
```

> **Pre-built vs. from source.** Only three images are TESAIoT-authored
> (`api`, `admin-ui`, `mqtt-bridge`); they are published to
> `ghcr.io/tesaiot/…` on every release as public, multi-arch images. The other
> services are upstream images pulled from their own registries. `PREBUILT=1`
> pulls the three pre-built images instead of building them, and falls back to a
> source build automatically if they cannot be pulled — so either command always
> produces an identical stack. Set `TESAIOT_REGISTRY` to use a mirror.

`make install` runs `scripts/install.sh`, which executes these steps in order
(it is **safe to re-run** at any time):

1. **Preflight** — checks Docker, ports, disk, `.env`.
2. **Secrets + first-run TLS** — creates `.env` with strong random secrets, the
   MongoDB keyfile, and a self-signed CA + server cert in `config/tls/`.
3. **Application images** — `docker compose build` (or, with `PREBUILT=1`,
   `docker compose pull` the pre-built images, falling back to a build).
4. **Bring up infrastructure** — `vault`, `mongodb`, `timescaledb`, `redis`,
   then waits for them to report healthy.
5. **Initialise Vault PKI** — `vault operator init` (3 key shares, threshold 2),
   unseal, build `pki-root` → `pki-int`, write roles/policies, enable AppRole.
   Unseal keys and root token are saved into `.env`.
6. **Start Vault Agent** — renders the API token and EMQX server certs.
7. **Initialise databases** — MongoDB replica set `rs0`, verify the
   `device_telemetry` hypertable.
8. **Bring up the application tier** — `api` (seeds the bootstrap admin), then
   `emqx`, `admin-ui`, `apisix`, `mqtt-bridge`, `nginx`.
9. **Provision broker + gateway** — EMQX bridge user, APISIX admin key + routes.
10. **Health check** — prints a status table and the access URLs.

When it completes you will see:

```
######## INSTALL COMPLETE ########

  Admin UI       :  https://localhost/          (via nginx 443)
  API            :  https://localhost/api/v1/   (internal-only :5566 - not published on the host)
  IoT mTLS ingest:  https://localhost:9444/
  EMQX dashboard :  http://localhost:18083          (user: admin)
  APISIX gateway :  http://localhost:9080  (admin :9180)
  Vault UI       :  http://localhost:8200/ui
```

Jump to [section 7 — First login](#7-first-login).

---

## 5. Path B — Manual step-by-step

Use this if you want to inspect or customise each stage.

### 5.1 Preflight

```bash
make preflight        # or: ./scripts/preflight-check.sh
```

### 5.2 Generate secrets, keyfile and first-run TLS

```bash
make secrets                          # or: ./scripts/generate-secrets.sh
# Bind a domain at the same time:
make secrets DOMAIN=iot.example.com
```

This copies `.env.example` → `.env`, replaces every `CHANGEME_*` with a random
secret, writes `config/mongodb/mongodb-keyfile`, generates a self-signed CA +
server cert in `config/tls/`, and **renders** the secret-bearing config
templates (`config/**/*.tpl` → the files docker-compose mounts: `emqx.conf`,
`auth-built-in-db-bootstrap.csv`, `config.yaml`, `apisix.yaml`,
`30-iot-mtls.conf`). Only the placeholder `.tpl` files are tracked in git; the
rendered files are `.gitignore`d and re-rendered from the pristine template on
every run, so they always match the current `.env`.

> **The generated admin password is stored in `.env` as `ADMIN_PASSWORD`.**
> Open `.env`, note it, and keep the file safe — it also holds the Vault unseal
> keys and root token.

You may edit `.env` now to set SMTP, change the domain, etc. (see
[configuration.md](configuration.md)).

### 5.3 Build images

```bash
make build            # docker compose build  (or: make pull — pre-built GHCR images)
```

### 5.4 Start Vault and initialise its PKI

**Order matters here.** `vault-agent` (and therefore the api's `depends_on`
chain) cannot become healthy until `init-pki` has written the AppRole
credentials — running `make up` before `make init-pki` deadlocks the first
boot. Start Vault alone first:

```bash
docker compose up -d vault
make init-pki         # ./scripts/init-vault-pki.sh
```

This initialises and unseals Vault, builds the two-tier PKI hierarchy
(`pki-root` → `pki-int`), creates the device/service roles, writes the API
policy, creates the AppRole used by `vault-agent`, and appends the Vault
client-CA chain to `config/tls/ca-bundle.pem` (what the nginx mTLS ingest
verifies device certs against).

### 5.5 Start the rest of the stack

```bash
make up               # docker compose up -d
```

### 5.6 Initialise databases

```bash
make init-db          # ./scripts/init-databases.sh
```

Initiates the MongoDB single-node replica set `rs0` and verifies the
`device_telemetry` hypertable created by `init-timescale.sql`.

### 5.7 Provision EMQX and APISIX

```bash
make init-emqx        # internal mqtt-bridge user in EMQX built-in auth DB
make init-apisix      # sync APISIX admin key, verify routes
docker compose restart apisix
```

### 5.8 Verify

```bash
make health
```

---

## 6. Generated secrets & certificates summary

After install, these files exist (all listed in `.gitignore` — **never commit them**):

| File | Created by | Contents |
|------|-----------|----------|
| `.env` | `generate-secrets.sh` + `init-vault-pki.sh` | all secrets, Vault unseal keys, root token, admin password |
| `config/mongodb/mongodb-keyfile` | `generate-secrets.sh` | MongoDB replica-set keyfile |
| `config/tls/server-cert.pem` / `server-key.pem` / `ca-bundle.pem` | `generate-secrets.sh` (self-signed first run; replaceable by Vault PKI) | nginx serverTLS + mTLS client CA |
| `config/vault-agent/secrets-unified/role-id` & `secret-id` | `init-vault-pki.sh` | AppRole credentials for vault-agent |
| `config/vault-agent/token-api/api-token` | vault-agent | Vault token the API uses to call PKI |
| `config/emqx/emqx.conf`, `config/emqx/auth-built-in-db-bootstrap.csv`, `config/apisix/config.yaml`, `config/apisix/apisix.yaml`, `config/nginx/conf.d/30-iot-mtls.conf` | `generate-secrets.sh` (rendered from the committed `*.tpl` templates) | mounted runtime configs with secrets baked in |

---

## 7. First login

1. Open **`https://localhost/`** (or `https://<your-domain>/`).
2. Accept the self-signed certificate warning (expected on first run).
3. Log in with the bootstrap admin:
   - **Email:** the `ADMIN_EMAIL` from `.env` (default `admin@localhost`, or
     `admin@<domain>` if you passed `--domain`).
   - **Password:** the `ADMIN_PASSWORD` from `.env`.
4. Change the admin password from the UI after first login.

See [user-management.md](user-management.md) to add more users and
[device-management.md](device-management.md) to register your first device.

---

## 8. Verify each service

Run the consolidated health check:

```bash
make health
```

You should see every row marked `UP`. For an end-to-end check (login, device
create, telemetry ingest, MQTT bridge, gateways) run the smoke test:

```bash
make smoke        # -> SUMMARY: 28/28 checks passed, 0 failed
```

See [verification.md](verification.md) for first-login details and per-service
checks. To verify services individually:

```bash
# Container status
docker compose ps

# Vault — should be initialised + unsealed
docker exec tesa-vault vault status

# MongoDB — replica set primary
docker exec tesa-mongodb mongosh --quiet --eval 'rs.status().myState'   # -> 1

# TimescaleDB — hypertable present
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -tAc \
  "SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name='device_telemetry';"  # -> 1

# Redis
docker exec tesa-redis sh -c 'redis-cli -a "$REDIS_PASSWORD" ping'   # -> PONG

# API health (the API is internal-only; probe via nginx or in-container)
curl -k https://localhost/api/v1/health                          # via nginx
docker exec tesa-api curl -fsS http://localhost:5566/api/v1/health  # in-container

# EMQX broker
docker exec tesa-emqx emqx ctl status

# APISIX gateway
curl -s http://localhost:9080/ -o /dev/null -w '%{http_code}\n'
```

If anything is not `UP`, see [troubleshooting.md](troubleshooting.md).

---

## 9. Next steps

- Replace the self-signed certs with Vault-PKI or Let's Encrypt certs →
  [security-tls-mtls.md](security-tls-mtls.md)
- Configure SMTP / OTP and add users → [user-management.md](user-management.md)
- Register devices and choose serverTLS or mTLS →
  [device-management.md](device-management.md)
- Set up backups → [backup-restore.md](backup-restore.md)
