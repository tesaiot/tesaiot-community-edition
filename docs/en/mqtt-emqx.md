<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# MQTT Broker (EMQX)

EMQX 5 is the MQTT broker. It exposes plain, serverTLS and mTLS listeners, and
delegates device/user authentication and authorization to the CE API over HTTP
webhooks. Configuration lives in `config/emqx/emqx.conf`.

---

## 1. Listeners

| Listener | Port | TLS | Client cert | Use |
|----------|------|-----|-------------|-----|
| `tcp.default` | `1883` | none | — | local / dev only |
| `ssl.servertls` | `8884` | serverTLS | not required (`verify_none`) | password auth over TLS |
| `ssl.mtls` | `8883` | mTLS | **required** (`verify_peer`, `fail_if_no_peer_cert`) | certificate identity |
| `ws.default` | `8083` | none | — | WebSocket (dev) |
| `wss.default` | `8084` | serverTLS | not required | WebSocket over TLS |
| dashboard | `18083` | http | — | admin UI (**keep private**) |

Server cert/key and the CA bundle are rendered into `/opt/emqx/etc/certs` by the
`vault-agent` (`key.pem`, `cert-with-chain.pem`, `vault-ca-bundle.pem`). Both
TLS listeners use TLS 1.2/1.3 with modern AES-GCM / CHACHA20 cipher suites.

---

## 2. Authentication chain

EMQX tries authenticators in order; an `ignore` result falls through to the next:

1. **Built-in database** — only the internal `mqtt-bridge` service account,
   bootstrapped from `config/emqx/auth-built-in-db-bootstrap.csv`. Always
   available, even while the API restarts.
2. **HTTP webhook** — for all real devices and users:
   ```
   POST http://tesa-api:5566/api/v1/emqx/auth
   Authorization: Bearer <EMQX_WEBHOOK_SECRET>
   body: username, password, clientid, peerhost, protocol, sockport,
         cert_common_name, cert_subject
   ```
   The API verifies the password (serverTLS) or the client-cert CN/serial (mTLS)
   against the MongoDB device registry + Vault PKI.

> The bearer secret must match on both sides — it is the `EMQX_WEBHOOK_SECRET`
> value, injected into `emqx.conf` and passed to the API automatically.

---

## 3. Authorization (ACL)

Topic/action authorization is delegated to the API:

```
POST http://tesa-api:5566/api/v1/emqx/acl
Authorization: Bearer <EMQX_WEBHOOK_SECRET>
body: username, topic, action, clientid, protocol, sockport
```

- `no_match = deny`, `deny_action = disconnect` — default-deny, drop on failure.
- ACL results are cached (max 10000 entries, TTL 1 minute).
- `config/emqx/acl.conf` provides a static fallback.

This lets the API enforce per-device topic scoping (e.g. a device may only
publish to `devices/<its-id>/#`).

---

## 4. The internal mqtt-bridge

`tesa-mqtt-bridge` connects to EMQX over serverTLS `8884` (validating the broker cert against the vault-agent-rendered CA bundle) as user `mqtt-bridge`
(password `MQTT_BRIDGE_PASSWORD`), subscribes to telemetry topics, and forwards
messages to the API, which writes them to TimescaleDB/MongoDB. The bridge runs
read-only with all capabilities dropped.

`init-emqx.sh` provisions / updates the `mqtt-bridge` user in the built-in auth
DB from `.env`; it is also seeded by the bootstrap CSV on first boot.

---

## 5. Connecting devices

### mTLS (port 8883)
```bash
mosquitto_pub -h <DOMAIN> -p 8883 \
  --cafile ca-bundle.pem \
  --cert device-cert.pem --key device-key.pem \
  -t "devices/sensor-01/telemetry" -m '{"temperature":23.5}'
```

### serverTLS (port 8884, username/password)
```bash
mosquitto_pub -h <DOMAIN> -p 8884 \
  --cafile ca-bundle.pem \
  -u sensor-01 -P "<device-password>" \
  -t "devices/sensor-01/telemetry" -m '{"temperature":23.5}'
```

The CA bundle comes from the Vault PKI (the device cert/key for mTLS, and the
serverTLS trust anchor, are obtained from the platform — see
[device-management.md](device-management.md)).

---

## 6. Dashboard & operations

```bash
docker exec tesa-emqx emqx ctl status          # broker status
docker exec tesa-emqx emqx ctl listeners       # listener state
docker exec tesa-emqx emqx ctl authn list      # authenticators
make logs s=emqx
```

EMQX dashboard: `http://localhost:18083` (user `admin`, password
`EMQX_DASHBOARD_PASSWORD`). **Do not expose `:18083` publicly.**

---

## 7. MQTT settings

From `emqx.conf`: max packet size 10 MB, QoS up to 2, retained messages enabled,
wildcard + shared subscriptions enabled, session expiry 2h, max inflight 32.
Tune these in `config/emqx/emqx.conf` and restart EMQX to apply.
