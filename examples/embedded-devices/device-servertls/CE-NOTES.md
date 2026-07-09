# Community Edition notes

This C (Mongoose) client is the serverTLS sibling of `../rpi-servertls`. It was
**verified end-to-end against a live CE install** in both modes.

## Build

```bash
# macOS: brew install openssl@3   |   Debian/Ubuntu: apt-get install -y libssl-dev
make all            # builds ./device_client (uses ../common-c)
```

## Provision & run

Register a serverTLS device, then populate `certs_credentials/`:

- `device_id.txt`      — the device id
- `mqtt_username.txt`  — the device id
- `mqtt_password.txt`  — from `POST /api/v1/devices/{id}/reset-mqtt-password`
- `api_key.txt`        — from `POST /api/v1/devices/{id}/regenerate-api-key`
- `ca-chain.pem`       — `cp ../../../config/tls/ca-bundle.pem certs_credentials/ca-chain.pem`

```bash
# MQTTS (serverTLS 8884)
COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8884 CERTS_DIR=$PWD/certs_credentials ./device_client

# HTTPS (REST /api/v1/telemetry, X-API-KEY)
COMM_MODE=HTTPS API_BASE_URL=https://localhost CERTS_DIR=$PWD/certs_credentials ./device_client
```

## CE adaptation applied

- `config.h`: `DEFAULT_API_BASE_URL`/`DEFAULT_MQTT_HOST` → `localhost`.
- **CA-trust fix** (`main.c`): the cloud build set `tls.ca_chain = NULL` for HTTPS
  (relying on the public OS trust store for `tesaiot.com`). CE's nginx edge is signed by
  the local Vault/bootstrap CA, so the HTTPS branch now keeps `ca-chain.pem` and leaves
  `verify_peer` on — no insecure fallback.
- HTTPS endpoint is `/api/v1/telemetry` (already built by the client from `API_BASE_URL`).

> Path note: `make` cannot `include ../common-c/mg_fetch.mk` if the repo lives under a
> directory whose name contains spaces. Clone into a space-free path to build.
