# สถาปัตยกรรม

เอกสารนี้อธิบายภาพรวมสถาปัตยกรรมของ TESAIoT Community Edition — การจัดวาง service, เครือข่าย,
volume และการไหลของข้อมูล

## ภาพรวม

Community Edition เป็น stack แบบ single-organization ที่จัดการด้วย Docker Compose ประกอบด้วย
11 services โดยตัด multi-tenancy ออก (ยุบ `organization_id` เป็นค่า `DEFAULT_ORG_ID` เดียว)

```
                          อินเทอร์เน็ต / LAN
                                  |
            +---------------------+----------------------+
            |                     |                      |
        nginx (80/443/9444)   apisix (9080/9443)   emqx (1883/8883/8884/8083/8084)
            |                     |                      |
            +----------+----------+                      |
                       |                                 |
                   api (5566)  <----- webhook auth/ACL --+
                   /  |  \                                |
        mongodb   redis  timescaledb                 mqtt-bridge
                                                          |
                                              forward telemetry -> api -> DB
        vault (8200) ---- vault-agent (render/renew certs) ---> emqx-certs (volume)
                       \-> token-api (Vault token ให้ api)
        admin-ui (React SPA) --- เสิร์ฟผ่าน nginx
```

## รายละเอียด service

| Service | อิมเมจ | บทบาท |
|---|---|---|
| `vault` | hashicorp/vault:1.18.3 | PKI 2 ชั้น (pki-root → pki-int) + secrets engine, auto-unseal |
| `vault-agent` | hashicorp/vault:1.18.3 | render + ต่ออายุใบรับรอง EMQX และ API token จาก Vault PKI อัตโนมัติ |
| `mongodb` | mongo:8.0 | ทะเบียนผู้ใช้/อุปกรณ์/ใบรับรอง — single-node replica set (`rs0`) |
| `timescaledb` | timescale/timescaledb:2.17.2-pg14 | telemetry time-series (hypertable) |
| `redis` | redis:7.4.4-alpine | cache + rate-limit storage (maxmemory 512mb, allkeys-lru) |
| `api` | tesa-api | Flask monolith + FastAPI mount สำหรับ device-management (พอร์ต 5566) |
| `admin-ui` | tesa-admin-ui | React SPA เสิร์ฟด้วย nginx (พอร์ต 80 ภายใน) |
| `emqx` | emqx/emqx:5.10.0 | MQTT broker — serverTLS + mTLS, auth/ACL ผ่าน API webhook |
| `mqtt-bridge` | tesa-mqtt-bridge | สะพาน telemetry: EMQX → API → TimescaleDB/MongoDB |
| `nginx` | nginx:1.27.5-alpine | TLS termination + reverse proxy (80/443/9444) |
| `apisix` | apache/apisix:3.11.0-debian | API gateway โหมด standalone YAML (ไม่ใช้ etcd) |

## เครือข่าย

stack ใช้ 2 เครือข่าย Docker bridge:

- **`tesa-external`** (`tesa-ext0`) — เฉพาะ edge proxy 2 ตัวที่ LAN เข้าถึง: `nginx`, `apisix`
- **`tesa-internal`** (`tesa-int0`) — traffic ภายในของฐานข้อมูลและ service ทั้งหมด

`api`, `emqx`, `vault` และฐานข้อมูล (mongodb, timescaledb, redis) อยู่บน `tesa-internal`
เท่านั้น — `api` ไม่ถูกเผยบน LAN bridge เลย (ดังนั้น device mTLS header จะถูก assert ได้
จาก nginx terminator เท่านั้น) และพอร์ต TLS ของ broker ที่หันออก LAN ถูก publish ตรงโดย
Docker ไม่ผ่าน edge bridge ออกแบบตามหลัก least-exposure

### พอร์ตที่ publish สู่ host

| Container | พอร์ตบน host | Exposure |
|-----------|--------------|----------|
| nginx | 80, 443, 9444 | public (HTTP redirect / serverTLS / mTLS ingest) |
| apisix | 9443 public; 9080, 9180 loopback | เฉพาะ 9443 หัน LAN |
| api | (ไม่ publish) | **ภายใน Docker network เท่านั้น** (ผ่าน nginx/APISIX) |
| emqx | 8883, 8884, 8084 public; 1883, 8083, 18083 loopback | เฉพาะ transport TLS หัน LAN |
| vault | 8200 loopback | operator บนเครื่องเท่านั้น |
| mongodb | (ไม่ publish) | **ภายใน Docker network เท่านั้น** |

> compose บังคับไว้แล้ว: พอร์ต management/plaintext ผูกกับ `127.0.0.1` ส่วน api/mongodb
> ไม่ publish เลย อุปกรณ์และเบราว์เซอร์ต้องการแค่ `443`, `9444`, `9443`, `8883` และ/หรือ
> `8884`/`8084`

## Volume (ข้อมูลถาวร)

| Volume | ใช้โดย | เก็บอะไร |
|---|---|---|
| `vault-data` | vault | storage + PKI ของ Vault |
| `vault-credentials` | vault | credential สำหรับ auto-unseal |
| `mongodb-data` | mongodb | ฐานข้อมูล MongoDB |
| `timescale-data` | timescaledb | ฐานข้อมูล TimescaleDB |
| `redis-data` | redis | snapshot ของ Redis |
| `emqx-data` | emqx | สถานะของ EMQX |
| `emqx-certs` | vault-agent → emqx/api/bridge | ใบรับรองที่ vault-agent render ออกมา (แชร์กัน) |

## การไหลของข้อมูล

### 1. การยืนยันตัวตนผู้ใช้ (Admin UI)

```
เบราว์เซอร์ -> nginx (443, TLS) -> api (5566) -> ตรวจสอบกับ mongodb -> ออก JWT
```

JWT เซ็นด้วย `JWT_SECRET` (HS256) rate-limit การ login เก็บใน Redis (per-IP)

### 2. การ ingest telemetry ผ่าน HTTP

```
อุปกรณ์ -> apisix (9443, key-auth X-API-Key) -> api (/api/v1/telemetry)
        -> เขียนลง TimescaleDB (+ MongoDB เมื่อเปิด dual storage)
```

### 3. การ ingest telemetry ผ่าน MQTT

```
อุปกรณ์ -> emqx (8883 mTLS / 8884 serverTLS) -- auth/ACL webhook --> api
        -> mqtt-bridge สมัครรับ topic -> forward เข้า api -> เขียนลง DB
```

### 4. วงจรชีวิตใบรับรอง

```
api -> Vault PKI (pki-int) ออก/เพิกถอนใบรับรองอุปกรณ์
vault-agent -> render ใบรับรองเซิร์ฟเวอร์ EMQX + ต่ออายุอัตโนมัติ -> emqx-certs volume
```

## การยุบ multi-tenant เป็น single-org

ในฉบับเต็ม ทุก entity ถูก scope ด้วย `organization_id` ใน CE ค่านี้ถูกตรึงไว้ที่
`DEFAULT_ORG_ID` (ค่าเริ่มต้น `default-org`) ส่งผ่านเข้า service ผ่าน environment โค้ดยังคงรับ
parameter org อยู่เพื่อความเข้ากันได้ แต่จะใช้ค่า default org เดียวเสมอ — **ห้ามเปลี่ยนค่านี้หลัง
boot ครั้งแรก** เพราะถูกเขียนลงในข้อมูล

## ความปลอดภัยระดับ container

แต่ละ service ใช้มาตรการ hardening:

- `no-new-privileges:true` กับเกือบทุก service
- `mqtt-bridge` ทำงานแบบ `read_only`, `cap_drop: ALL`, tmpfs สำหรับ `/tmp`
- vault ใช้ `cap_add: IPC_LOCK` เพื่อ lock memory
- resource limit (cpus/memory) ทุก service
- log แบบ json-file หมุนเวียน (max 10m × 3 ไฟล์)

## ดูเพิ่มเติม

- [security-tls-mtls.md](security-tls-mtls.md) — โหมด TLS/mTLS
- [certificate-lifecycle.md](certificate-lifecycle.md) — วงจรชีวิตใบรับรอง
- [api-gateway-apisix.md](api-gateway-apisix.md) — เกตเวย์
- [mqtt-emqx.md](mqtt-emqx.md) — โบรกเกอร์
