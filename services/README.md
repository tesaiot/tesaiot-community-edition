<!--
SPDX-FileCopyrightText: 2026 TESAIoT Platform contributors
SPDX-License-Identifier: Apache-2.0
-->

# `services/` — Build-from-source services

This directory contains **only the application services that TESAIoT authors and
builds from source**. Everything else in the platform runs as a **pinned,
official upstream Docker image** configured through the top-level [`../config/`](../config/)
directory — not vendored here.

> **Why so few?** A self-host platform should not fork or copy the source of
> third-party infrastructure (HashiCorp Vault, EMQX, Apache APISIX, MongoDB,
> TimescaleDB, Redis, nginx). Doing so mixes licenses, makes security patching
> hard, and bloats the repository. Instead we pin official image versions in
> [`../docker-compose.yml`](../docker-compose.yml) and mount our configuration.
> This is the same pattern CNCF-graduated infrastructure projects follow.

---

## The 3 build services

| Service | Build context | Image tag | Stack | Port(s) | Role |
|---|---|---|---|---|---|
| **api** | `./services/api` | `tesa-api` | Python — Flask monolith + FastAPI device-management mount (served by gunicorn) | `5566` | Core REST API: user management, device/identity management, certificate lifecycle (Vault PKI), telemetry & dashboard endpoints |
| **admin-ui** | `./services/admin-ui` | `tesa-admin-ui` | React + Vite, served by nginx (pinned `nginx:1.27.5-alpine3.21`) | behind `nginx` (443) | Admin web console: users, devices, certificates, and the IoT telemetry dashboard inside Device Details |
| **mqtt-bridge** | `./services/mqtt-bridge` | `tesa-mqtt-bridge` | Python | none (egress only) | Subscribes to EMQX, normalises telemetry, and forwards it over HTTP to the `api` (which persists to TimescaleDB / MongoDB — the bridge never writes the databases directly) |

Build tags are parameterised as `${BUILD_TAG:-latest}` in `docker-compose.yml`.

---

## How the 8 capabilities map across the repo

The 8 in-scope capabilities are delivered by **these 3 source services + pinned
upstream images + config**, not by one folder per capability:

| # | Capability | Source service(s) | Upstream image + config |
|---|---|---|---|
| 1 | User Management | `api`, `admin-ui` | — |
| 2 | Device / Identity Management | `api`, `admin-ui` | — |
| 3 | serverTLS & mTLS | — | `nginx`, `emqx`, `apisix` + `config/nginx`, `config/emqx`, `config/apisix` |
| 4 | Certificate Life-cycle (Vault PKI) | `api` | `vault` (`hashicorp/vault`) + `config/vault*` |
| 5 | APISIX API Gateway | — | `apache/apisix` + `config/apisix` |
| 6 | EMQX MQTT Broker | `mqtt-bridge` | `emqx/emqx` + `config/emqx` |
| 7 | MongoDB & TimescaleDB | `api`, `mqtt-bridge` | `mongo`, `timescale/timescaledb` + `config/mongodb`, `config/timescaledb` |
| 8 | IoT Telemetry Dashboard (in Device Details) | `admin-ui`, `api`, `mqtt-bridge` | — |

---

## Full runtime topology (11 containers)

Defined in [`../docker-compose.yml`](../docker-compose.yml):

**Built from source (this directory):**
- `api` → `5566`
- `admin-ui` → served via `nginx`
- `mqtt-bridge` → no published port

**Pinned upstream images (configured via `../config/`):**

| Container | Image | Key ports |
|---|---|---|
| `vault` | `hashicorp/vault:1.18.3` | `8200` |
| `vault-agent` | `hashicorp/vault:1.18.3` | — (renders certs/tokens) |
| `mongodb` | `mongo:8.0` | `27017` |
| `timescaledb` | `timescale/timescaledb:2.17.2-pg14` | `5432` |
| `redis` | `redis:7.4.4-alpine` | `6379` |
| `emqx` | `emqx/emqx:5.10.0` | `1883` (plain), `8883` (mTLS), `8884` (serverTLS), `8083/8084` (WS/WSS), `18083` (dashboard) |
| `nginx` | `nginx:1.27.5-alpine3.21` | `80`, `443`, `9444` |
| `apisix` | `apache/apisix:3.11.0-debian` | `9080` (http), `9443` (https/mTLS), `9180` (admin) |

> Exact image versions are the single source of truth in `../docker-compose.yml`.
> To upgrade an upstream component, bump its tag there — no source changes needed.

---

## ภาษาไทย — สรุป

โฟลเดอร์ `services/` เก็บ **เฉพาะโค้ดที่ TESAIoT เขียนเองและต้อง build จากซอร์ส** เท่านั้น
มี 3 ตัว:

- **api** — Python (Flask + FastAPI device-management) พอร์ต `5566` : API หลักสำหรับ
  user, device/identity, certificate lifecycle, telemetry/dashboard
- **admin-ui** — React + Vite (เสิร์ฟผ่าน nginx) : หน้าเว็บแอดมิน รวม telemetry
  dashboard ใน Device Details
- **mqtt-bridge** — Python : รับ telemetry จาก EMQX แล้วส่งต่อผ่าน HTTP ไปยัง `api`
  (ตัว api เป็นผู้เขียนลง TimescaleDB / MongoDB — bridge ไม่เขียนฐานข้อมูลโดยตรง)

ความสามารถที่เหลือ (Vault, EMQX, APISIX, MongoDB, TimescaleDB, Redis, nginx) **ใช้
official image ที่ pin เวอร์ชันไว้** แล้ว mount คอนฟิกจาก [`../config/`](../config/)
เข้าไป — เราไม่ copy ซอร์สของซอฟต์แวร์บุคคลที่สามมาไว้ในนี้ เพราะจะทำให้ license
ปนกัน, แพตช์ security ยาก และ repo บวม (เป็นแนวทางเดียวกับโปรเจกต์ infra ระดับ CNCF)
ทั้งหมดประกอบกันเป็น 11 containers ใน [`../docker-compose.yml`](../docker-compose.yml)
