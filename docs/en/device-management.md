<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Device / Identity Management

A "device" in TESAIoT Community Edition is a record in MongoDB (`devices`
collection) bound to a cryptographic identity — either a username/password
(serverTLS) or an X.509 client certificate from Vault PKI (mTLS), plus an
optional API key for HTTPS telemetry. This document covers registering and
managing devices and their identities.

---

## 1. Device lifecycle overview

```
register ─► assign identity ─► connect & send telemetry ─► monitor ─► renew/revoke ─► retire
            (password / cert / API key)                      (Device Details + dashboard)
```

Each device record carries at least: `device_id` (unique), name/metadata,
status, the chosen auth mode, and identity references (e.g.
`certificate_serial`, API key id). `device_id` has a unique index;
`certificate_serial` is indexed for cert lookups.

---

## 2. Registering a device

### Via the Admin UI
Open **Devices → Add device**, give it a name and `device_id`, choose the
authentication mode (serverTLS password or mTLS certificate), and save. The UI
walks you through downloading credentials / certificate or showing a QR code.

### Via the API (prefix `/api/v1/devices`, admin JWT)

| Method & path | Purpose |
|---------------|---------|
| `GET  /api/v1/devices/` | List devices. |
| `POST /api/v1/devices/` | Create a device. |
| `GET  /api/v1/devices/<id>` | Get one device. |
| `PUT  /api/v1/devices/<id>` | Update a device. |
| `DELETE /api/v1/devices/<id>` | Delete a device. |
| `PUT  /api/v1/devices/<id>/status` | Enable / disable. |
| `GET  /api/v1/devices/stats` | Fleet statistics. |
| `POST /api/v1/devices/bulk-import` | CSV bulk import (`/bulk-import/template`, `/bulk-import/validate-csv`). |

Create a device:

```bash
TOKEN=<admin access_token>
curl -k -X POST https://localhost/api/v1/devices/ \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"device_id":"sensor-01","name":"Workshop sensor","auth_mode":"mtls"}'
```

---

## 3. Device identities

### 3.1 Certificate (mTLS)

| Method & path | Purpose |
|---------------|---------|
| `GET  /api/v1/devices/<id>/certificate/info` | Cert metadata (serial, expiry). |
| `GET  /api/v1/devices/<id>/certificate/download/<type>` | Download cert / key / CA. |
| `POST /api/v1/devices/<id>/certificate/renew` | Re-issue from Vault PKI. |
| `POST /api/v1/devices/<id>/certificate/revoke` | Revoke the cert. |
| `GET\|POST /api/v1/devices/<id>/public-key` | Manage / submit a device public key (CSR flow). |

The certificate is issued from the Vault PKI `iot-device-ecc` / `device-cert` /
`csr-signing` roles and recorded in the `certificates` collection. See
[certificate-lifecycle.md](certificate-lifecycle.md).

### 3.2 Password (serverTLS)

| Method & path | Purpose |
|---------------|---------|
| `POST /api/v1/devices/<id>/reset-password` | Generate / reset the MQTT password. |
| `GET  /api/v1/devices/<id>/password/view/<token>` | One-time password reveal. |

The password is validated by EMQX via the API auth webhook on the serverTLS
listener (`:8884`).

### 3.3 API key (HTTPS telemetry via APISIX)

| Method & path | Purpose |
|---------------|---------|
| `POST /api/v1/devices/<id>/regenerate-api-key` | (Re)issue the device API key. |

The key is presented as `X-API-Key` to APISIX, which applies a route-level
rate limit (shared, not per-device in standalone mode) and forwards to the API,
where the key is validated and per-key limits are enforced. See
[api-gateway-apisix.md](api-gateway-apisix.md).

### 3.4 QR / zero-touch provisioning

| Method & path | Purpose |
|---------------|---------|
| `GET  /api/v1/devices/<id>/qrcode` | Enrollment QR code. |
| `POST /api/v1/devices/qrcode/scan` | Complete enrollment from a scanned QR. |
| `POST /api/v1/devices/provision/zero-touch` | Zero-touch provisioning. |

The QR encodes the public ingest URLs (`TESA_PUBLIC_*` in `.env`).

---

## 4. Choosing serverTLS vs mTLS

| | serverTLS | mTLS |
|---|-----------|------|
| Device identity | username + password | X.509 client cert |
| MQTT port | `8884` | `8883` |
| HTTPS ingest | `443` (API key/password) | `9444` (client cert) |
| Setup effort | low | higher (cert provisioning) |
| Assurance | medium | high |

You can mix modes across the fleet. See
[security-tls-mtls.md](security-tls-mtls.md) for the full flow.

---

## 5. Sending telemetry from a device

### MQTT (preferred)
Publish to a device-scoped topic; the broker authorizes via the API ACL webhook
and the bridge forwards it to TimescaleDB:

```bash
# mTLS
mosquitto_pub -h <DOMAIN> -p 8883 \
  --cafile ca-bundle.pem --cert device-cert.pem --key device-key.pem \
  -t "devices/sensor-01/telemetry" -m '{"temperature":23.5}'

# serverTLS (username/password)
mosquitto_pub -h <DOMAIN> -p 8884 --cafile ca-bundle.pem \
  -u sensor-01 -P "<device-password>" \
  -t "devices/sensor-01/telemetry" -m '{"temperature":23.5}'
```

### HTTPS
```bash
# Via APISIX with an API key
curl -k -X POST https://<DOMAIN>:9443/api/v1/devices/sensor-01/telemetry \
  -H "X-API-Key: <device-api-key>" -H 'Content-Type: application/json' \
  -d '{"temperature":23.5}'

# Via nginx mTLS ingest with a client certificate
curl --cert device-cert.pem --key device-key.pem --cacert ca-bundle.pem \
  -X POST https://<DOMAIN>:9444/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"sensor-01","temperature":23.5}'
```

---

## 6. Monitoring devices

- **Device Details** in the Admin UI shows status, identity, certificate health,
  and the live **Telemetry Dashboard** (see
  [telemetry-dashboard.md](telemetry-dashboard.md)).
- `GET /api/v1/devices/<id>/health`, `/status`, `/logs`, `/telemetry/last`.
- Certificate monitoring: `GET /api/v1/certificates/expiring`,
  `/renewal-candidates`, `/device/<id>/status`.
