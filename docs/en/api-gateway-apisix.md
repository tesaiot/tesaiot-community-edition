<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# API Gateway (Apache APISIX)

APISIX is the edge API gateway for device-facing HTTP traffic. In CE it runs
in **standalone YAML mode** — routes, consumers and TLS material are declared in
`config/apisix/apisix.yaml` and loaded at boot, so **no etcd is required**.

---

## 1. Ports

| Port | Purpose | Exposure |
|------|---------|----------|
| `9080` | HTTP gateway | public |
| `9443` | HTTPS gateway (serverTLS / optional mTLS) | public |
| `9180` | Admin API | **keep private** |

The admin key (`APISIX_ADMIN_KEY` in `.env`) is injected into
`config/apisix/config.yaml` by `init-apisix-routes.sh`.

---

## 2. Declared routes

From `config/apisix/apisix.yaml`:

| Route id | URI | Methods | Plugins | Upstream |
|----------|-----|---------|---------|----------|
| `device-telemetry-ip` | `/api/v1/telemetry` | POST, OPTIONS | key-auth, limit-req (1000/2000), cors, response-rewrite | `tesa-api:5566` |
| `device-telemetry-device-id` | `/api/v1/devices/*/telemetry` | POST, OPTIONS | key-auth, limit-req (1000/2000), proxy-rewrite | `tesa-api:5566` |
| `api-backend` | `/api/*` | all | — | `tesa-api:5566` |
| `admin-ui` | `/*` | all | — | `tesa-admin-ui:80` |

- **key-auth**: device API key via `X-API-Key` header or `?api_key=` query;
  credentials are hidden from the upstream.
- **limit-req**: 1000 req/s steady, 2000 burst; rejects with `429` and a clear
  message. The `key: consumer_name` field differentiates only the consumers
  statically declared in `apisix.yaml`. In the CE's standalone YAML mode there
  is a single sample consumer and **no dynamic per-device consumers**, so this
  is effectively a **route-level (shared) limit**, not a per-device quota. True
  per-device limits are enforced by the API backend, not the gateway.
- **cors**: permissive for telemetry POSTs (tighten `allow_origin` in production).

---

## 3. Consumers (static, single sample)

APISIX consumers map an API key to a named consumer. In the CE's standalone YAML
mode the consumer list is **static** (loaded from `apisix.yaml` at boot; the file
is mounted read-only and the Admin API cannot mutate runtime state). The shipped
sample:

```yaml
consumers:
  - username: "device_sample"
    plugins:
      key-auth:
        key: "CHANGEME_DEVICE_API_KEY_SAMPLE"   # rotated by generate-secrets.sh
      limit-req:
        rate: 1000
        burst: 2000
        key: "consumer_name"
```

> The sample key is replaced with a random value by `generate-secrets.sh`.
> **Rotate / remove it before production.** Real per-device keys are issued by
> the API (`POST /api/v1/devices/<id>/regenerate-api-key`) and are **validated by
> the API backend** (`api_key_service.py`) -- they are **not** registered as
> APISIX consumers in standalone mode. To get true per-device gateway consumers
> you must run APISIX with an etcd control plane (out of scope for the CE).

Send telemetry through the gateway:

```bash
curl -k -X POST https://<DOMAIN>:9443/api/v1/devices/sensor-01/telemetry \
  -H "X-API-Key: <device-api-key>" -H 'Content-Type: application/json' \
  -d '{"temperature": 23.5}'
```

---

## 4. serverTLS on the gateway

The `ssls` block in `apisix.yaml` holds the server certificate (SNIs
`localhost`, `tesa.iot`). `generate-secrets.sh` injects the first-run
self-signed cert/key; replace them with a Vault-PKI `platform-service`
certificate for production (see
[security-tls-mtls.md](security-tls-mtls.md) §4) and `docker compose restart
apisix`.

---

## 5. Enabling mTLS on the gateway (optional)

mTLS routes are **not** loaded by default. To enable:

1. Add a `client` block to the `ssls` entry in `apisix.yaml`:
   ```yaml
   ssls:
     - id: 1
       snis: ["<DOMAIN>"]
       cert: |
         -----BEGIN CERTIFICATE-----
         ...
       key: |
         -----BEGIN PRIVATE KEY-----
         ...
       client:
         ca: |
           -----BEGIN CERTIFICATE-----    # Vault PKI issuing CA / ca_chain
           -----END CERTIFICATE-----
         depth: 2
         verify_client: true
   ```
2. Merge the route patterns from `config/apisix/mtls-routes.yaml` into the
   `routes:` list. They use the `client-control` plugin to whitelist device-cert
   CNs (e.g. `CN=*.device.tesa.iot`) after TLS validates the client cert against
   the Vault PKI CA, plus `request-validation` and tighter rate limits.
3. `docker compose restart apisix`.

---

## 6. Operations

```bash
make init-apisix                 # sync admin key + verify routes
docker compose restart apisix    # apply config changes
make logs s=apisix               # view logs

# Read loaded routes via the admin API (from inside the container)
docker exec tesa-apisix sh -c \
  "wget -q -O- --header='X-API-KEY: $APISIX_ADMIN_KEY' http://127.0.0.1:9180/apisix/admin/routes"
```

> Because CE uses standalone YAML mode, the source of truth is
> `config/apisix/apisix.yaml`. Edit that file and restart — the Admin API is
> available mainly for inspection.
