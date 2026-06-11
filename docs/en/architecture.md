<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Architecture

TESAIoT Community Edition is an 11-container Docker Compose stack designed to run on
a single host for a single organization.

---

## 1. Components

| # | Container | Image | Role |
|---|-----------|-------|------|
| 1 | `tesa-vault` | `hashicorp/vault:1.18.3` | PKI (root + intermediate CA), KV secrets, device cert storage. |
| 2 | `tesa-vault-agent` | `hashicorp/vault:1.18.3` | Authenticates via AppRole, renders & auto-renews the API token and EMQX/service certs. |
| 3 | `tesa-mongodb` | `mongo:8.0` | Registry: users, devices, certificates, organizations, MQTT permissions, audit logs. Single-node replica set `rs0`. |
| 4 | `tesa-timescaledb` | `timescale/timescaledb:2.17.2-pg14` | Time-series telemetry, events, audit (hypertables + continuous aggregates). |
| 5 | `tesa-redis` | `redis:7.4.4-alpine` | Cache + rate-limit storage for the API. |
| 6 | `tesa-api` | built `tesa-api` (Flask, Python 3.11) | Core REST API on `:5566`: auth, users, devices, certs, telemetry, EMQX auth/ACL webhooks. |
| 7 | `tesa-admin-ui` | built `tesa-admin-ui` (React SPA via nginx) | Admin console + the Telemetry Dashboard inside Device Details. |
| 8 | `tesa-emqx` | `emqx/emqx:5.10.0` | MQTT broker: plain/serverTLS/mTLS listeners, webhook auth/ACL. |
| 9 | `tesa-mqtt-bridge` | built `tesa-mqtt-bridge` | Subscribes to EMQX, forwards telemetry to the API → TimescaleDB/MongoDB. Runs read-only, no capabilities. |
| 10 | `tesa-nginx` | `nginx:1.27.5-alpine3.21` | Edge TLS termination + reverse proxy (`:80` redirect, `:443` serverTLS, `:9444` mTLS ingest). |
| 11 | `tesa-apisix` | `apache/apisix:3.11.0-debian` | API gateway in standalone YAML mode (no etcd): API-key auth, rate limiting, serverTLS/mTLS. |

---

## 2. Networks

Two bridge networks isolate backend traffic from edge traffic:

| Network | Compose name | Members | Purpose |
|---------|-------------|---------|---------|
| `tesa-external` | `tesa-ext0` | nginx, apisix | LAN-reachable edge only. |
| `tesa-internal` | `tesa-int0` | all services | Backend-only data/service traffic. |

Only the two edge proxies sit on `tesa-external`. `api`, `emqx`, `vault` and the
data stores are reachable **only** on `tesa-internal` — the API is never exposed
on the LAN bridge (so device mTLS headers can only be asserted by the nginx
terminator), and the broker's LAN-facing TLS ports are published directly by
Docker rather than via the edge bridge.

Data stores (`mongodb`, `timescaledb`, `redis`) live **only** on the internal
network. The application reaches them by stable network aliases
(`tesa-mongodb`, `tesa-timescaledb`, `tesa-redis`, `tesa-vault`, `tesa-api`, …).

---

## 3. Port map

| Container | Host port(s) | Protocol | Exposure |
|-----------|--------------|----------|----------|
| nginx | 80, 443, 9444 | HTTP redirect / serverTLS / mTLS ingest | public |
| apisix | 9443 public; 9080, 9180 loopback | HTTPS gateway / HTTP / admin API | only 9443 faces the LAN |
| api | (none) | HTTP `:5566` | **not published** — internal Docker network only (via nginx/APISIX) |
| emqx | 8883, 8884, 8084 public; 1883, 8083, 18083 loopback | mTLS / serverTLS / WSS / plain MQTT / WS / dashboard | only the TLS transports face the LAN |
| vault | 8200 loopback | HTTP API + UI | local operator access only |
| mongodb | (none) | MongoDB wire `:27017` | **not published** — internal Docker network only |

> The compose file already enforces this: management/plaintext ports are bound
> to `127.0.0.1`, and the api/mongodb are not published at all. Devices and
> browsers only need `443`, `9444`, `9443`, `8883` and/or `8884`/`8084`.

---

## 4. Request flows

### 4.1 Operator using the Admin UI
```
Browser --443 serverTLS--> nginx --/--> admin-ui (React SPA)
                                --/api--> tesa-api --> MongoDB / TimescaleDB / Redis
```

### 4.2 Device sending telemetry over MQTT
```
Device --8883 mTLS / 8884 serverTLS--> EMQX
   EMQX --POST /api/v1/emqx/auth--> tesa-api   (authenticate)
   EMQX --POST /api/v1/emqx/acl --> tesa-api   (authorize topic/action)
   Device --PUBLISH telemetry--> EMQX --> mqtt-bridge --> tesa-api --> TimescaleDB
```

### 4.3 Device sending telemetry over HTTPS
```
Device --9444 mTLS--> nginx (forwards client-cert headers) --> tesa-api --> TimescaleDB
   or
Device --9080/9443 + X-API-Key--> APISIX (key-auth, rate limit) --> tesa-api --> TimescaleDB
```

### 4.4 Certificate issuance
```
tesa-api --(api-token)--> Vault PKI (pki-int/issue or sign) --> X.509 cert
vault-agent --(AppRole)--> Vault PKI --> renders EMQX server cert + renews API token
```

---

## 5. Startup ordering & health

Compose `depends_on` + healthchecks enforce a safe boot order:

```
vault (healthy)
  └─ vault-agent (produces api-token + certs)
mongodb, timescaledb, redis (healthy)
  └─ api (seeds bootstrap admin, healthy)
       ├─ admin-ui
       ├─ emqx
       ├─ apisix
       ├─ mqtt-bridge
       └─ nginx
```

Every service defines a Docker healthcheck; `make health` probes them and prints
a status table.

---

## 6. Persistence

Named Docker volumes (survive `make down`, destroyed only by `make clean` /
`teardown --volumes`):

| Volume | Holds |
|--------|-------|
| `vault-data` | Vault storage (PKI, KV). |
| `vault-credentials` | Vault credential material. |
| `mongodb-data` | MongoDB databases. |
| `timescale-data` | TimescaleDB databases. |
| `redis-data` | Redis snapshots (AOF/RDB). |
| `emqx-data` | EMQX runtime data. |
| `emqx-certs` | Shared: vault-agent renders certs → emqx + api + bridge read them. |

---

## 7. Single-organization model

The original platform is multi-tenant. CE collapses this to one organization:

- `init-mongo.js` creates a single `Default Organization` keyed by
  `DEFAULT_ORG_ID`.
- `organization_id` columns/fields are **retained** in the schema so application
  queries and indexes keep working unchanged.
- The API always reads/writes `DEFAULT_ORG_ID` — there is no org switching,
  org creation, or cross-org scoping.

This keeps the code paths intact and stable while removing all multi-tenant
surface area.
