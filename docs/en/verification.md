<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Verifying the installation

After `make install`, use this guide to confirm every service is actually
working and to learn where to sign in.

## 1. First login

| | |
|---|---|
| **Admin UI** | `https://localhost/` (or `https://<your-domain>/`) |
| **Sign in with** | the **email** address in `ADMIN_EMAIL` (default `admin@localhost`) |
| **Password** | the value of `ADMIN_PASSWORD` in your generated `.env` |

The first-run TLS certificate is self-signed, so your browser will warn on the
first visit — accept it (or replace it with a Vault-PKI / Let's Encrypt cert as
described in [security-tls-mtls.md](security-tls-mtls.md)). Change the admin
password from the UI after the first login.

> The login form authenticates by **email**, not username.

### Other endpoints

| Service | URL | Notes |
|---------|-----|-------|
| Admin UI + Telemetry Dashboard | `https://localhost/` | nginx :443 |
| REST API | `https://localhost/api/v1/` | `:5566` is internal-only |
| IoT mTLS telemetry ingest | `https://localhost:9444/` | |
| EMQX dashboard | `http://localhost:18083` | user `admin`; password = `EMQX_DASHBOARD_PASSWORD` in `.env` |
| APISIX gateway | `http://localhost:9080` (admin `:9180`) | |
| Vault UI | `http://localhost:8200/ui` | token = `VAULT_ROOT_TOKEN` in `.env` |
| MQTT | `:8883` mTLS · `:8884` serverTLS · `:8083` WS · `:8084` WSS | |

## 2. Health check

```bash
make health
```

You should see every row marked `UP` and a summary of `N up, 0 down`.

## 3. End-to-end smoke test

A self-contained smoke test exercises **all 11 containers plus the real IoT
flows** — admin login (JWT), device create, telemetry ingest, the MQTT bridge,
the edge (nginx / APISIX), the broker (EMQX), Vault PKI and both databases:

```bash
make smoke
# or:  python3 scripts/smoke-test.py        (add -v for per-check detail)
```

- It reads credentials and secrets from `.env` automatically.
- Override the admin login with `ADMIN_EMAIL=… ADMIN_PASSWORD=… python3 scripts/smoke-test.py`.
- It requires only the Python 3 standard library (no extra packages).
- **Exit code 0** = every check passed (suitable for CI); **1** = at least one failed.

Expected result:

```
SUMMARY: 28/28 checks passed, 0 failed
```

## 4. Verify services individually

```bash
# Container status
docker compose ps

# Vault — initialised + unsealed
docker exec tesa-vault vault status

# MongoDB — replica set primary (-> 1)
docker exec tesa-mongodb mongosh --quiet --eval 'rs.status().myState'

# TimescaleDB — telemetry hypertable present (-> 1)
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -tAc \
  "SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name='device_telemetry';"

# Redis (-> PONG)
docker exec tesa-redis sh -c 'redis-cli -a "$REDIS_PASSWORD" ping'

# API health (via nginx)
curl -k https://localhost/api/v1/health

# EMQX broker
docker exec tesa-emqx emqx ctl status

# APISIX gateway
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:9080/
```

If anything is not healthy, see [troubleshooting.md](troubleshooting.md).

## 5. Organization API keys

Sign in as an admin and open **API Keys** in the sidebar to issue API keys for
the REST API / gateway. In the Community Edition these keys are stored in
MongoDB and validated by the API tier (APISIX runs in standalone YAML mode, so
there are no per-consumer gateway keys). Each key is shown in full exactly once,
at creation/rotation time; only a hash and a short prefix are stored. See
[api-gateway-apisix.md](api-gateway-apisix.md).
