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

An organization key (prefix `tesaiot_org_…`) authenticates the read API, so you
can pull device telemetry straight through the APISIX gateway — no browser
session required. Pass it as the `X-API-Key` header (or `?api_key=`):

```bash
# Read the latest telemetry for a device through the gateway (:9443)
curl -k https://localhost:9443/api/v1/devices/<device_id>/telemetry/last \
  -H "X-API-Key: tesaiot_org_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

The key is read-only and scoped to its organization; an invalid or revoked key
returns `401`.

## 6. Device telemetry over MQTT (serverTLS and mTLS)

Both device authentication modes publish to the same broker and land in the
time-series store. Create a device in the UI (or via the API), then:

- **serverTLS (`:8884`)** — the device authenticates with its **device id as the
  MQTT username** and the generated MQTT password, over a TLS connection that
  verifies the broker certificate. Publish JSON to
  `device/<device_id>/telemetry`.
- **mTLS (`:8883`)** — create the device with `auth_mode: mtls`, generate its
  certificate (Device → Certificate → *Generate/Renew*, or
  `POST /api/v1/devices/<id>/certificate/renew`), and download the
  client certificate + key (Vault PKI issues an EC P-256 client cert). The
  device presents that certificate; the broker verifies it at the TLS handshake
  and the API webhook authorizes it by certificate CN. Present the **device id
  as the MQTT username** as well (it must equal the certificate CN).

After publishing, the sample is queryable from the time-series tier:

```bash
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -tAc \
  "SELECT count(*) FROM telemetry_generic WHERE device_id='<device_id>';"
```

and through the read API / gateway as in §5.

## 7. Verifying the pre-built images (signature, SBOM, provenance)

The three TESAIoT-authored images published to `ghcr.io/tesaiot/…` are
**keyless-signed with [cosign](https://docs.sigstore.dev/)** and carry an
**SBOM** and **SLSA build provenance**, so you can prove an image was built by
this repository's CI from this source — not tampered with.

```bash
# Verify the signature (identity = this repo's release workflow)
cosign verify ghcr.io/tesaiot/tesa-api:1.1.3 \
  --certificate-identity-regexp '^https://github.com/tesaiot/tesaiot-community-edition/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# Inspect the attached SBOM and provenance attestations
docker buildx imagetools inspect ghcr.io/tesaiot/tesa-api:1.1.3 \
  --format '{{ json .Provenance }}'
cosign download sbom ghcr.io/tesaiot/tesa-api:1.1.3
```

Repeat for `tesa-admin-ui` and `tesa-mqtt-bridge`. A failed `cosign verify`
means the image is not the official build — do not run it.
