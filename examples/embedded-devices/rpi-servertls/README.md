<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# serverTLS Device Client (Python)

A minimal Python client that authenticates to **TESAIoT Community Edition** with
**server TLS** and streams telemetry two ways:

- **MQTT mode** — publishes to EMQX over serverTLS (`localhost:8884`), authenticated
  with the device username/password.
- **HTTPS mode** — POSTs to the REST ingest endpoint with the device API key.

It maps to CE capabilities **#3 serverTLS**, **#5 APISIX key-auth**, **#6 EMQX broker**,
**#7 TimescaleDB**, and **#8 telemetry dashboard**.

> **Verified on a live CE install.** MQTT mode was run end-to-end against a running
> stack: 5 publishes landed as 15 rows in the `device_telemetry` hypertable. See
> `TESAIoT_PLAN/examples-vv-evidence.md` for the evidence.

## Prerequisites

- A running Community Edition (`make install` / `docker compose up`).
- A device registered in the Admin UI (or via the API) with **auth mode = serverTLS**.
- The CE CA bundle copied to `certs/ca.pem` (see `certs/README.md`).

## 1. Provision credentials

From the CE host (admin JWT required):

```bash
# serverTLS MQTT password (shown once)
curl -sk -X POST https://localhost/api/v1/devices/<DEVICE_ID>/reset-mqtt-password \
  -H "Authorization: Bearer <ADMIN_JWT>" -H 'Content-Type: application/json' -d '{}'

# device API key for REST mode (shown once, prefix tesa_dak_)
curl -sk -X POST https://localhost/api/v1/devices/<DEVICE_ID>/regenerate-api-key \
  -H "Authorization: Bearer <ADMIN_JWT>" -H 'Content-Type: application/json' -d '{}'
```

## 2. Configure

```bash
cp .env.example .env
# edit DEVICE_ID / MQTT_USERNAME / MQTT_PASSWORD / API_KEY
cp ../../../config/tls/ca-bundle.pem certs/ca.pem
```

## 3. Run

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# MQTT (serverTLS) — verified path
./.venv/bin/python main.py --mode mqtt --interval 5

# HTTPS (REST)
./.venv/bin/python main.py --mode https --interval 5
```

Watch the point arrive in **Admin UI → Devices → Device Details → Telemetry**, or query
TimescaleDB directly:

```sql
SELECT time, metric_name, metric_value
FROM device_telemetry WHERE device_id='<DEVICE_ID>' ORDER BY time DESC LIMIT 10;
```

## Community Edition notes

- The MQTT publish topic is `device/<DEVICE_ID>/telemetry`, which the CE
  `mqtt-bridge` subscribes to and forwards to TimescaleDB.
- The REST endpoint is `POST {API_BASE_URL}/api/v1/telemetry` with body
  `{"device_id": ..., "data": {...}}` — **not** the cloud path
  `/devices/{id}/telemetry`.
- **Known CE issue affecting HTTPS mode:** the nginx edge (`:443`) currently presents a
  server certificate signed by a first-boot **Bootstrap CA that lacks the `keyUsage`
  extension**, which strict TLS clients (Python `requests`) reject even with the correct
  CA bundle. Until the platform re-issues the nginx cert from the Vault PKI (or adds
  `keyUsage` to the Bootstrap CA), HTTPS mode requires that fix. **Do not** disable TLS
  verification. MQTT mode is unaffected — EMQX chains to the Vault Intermediate CA.
  See `TESAIoT_PLAN/examples-vv-evidence.md` §4.
