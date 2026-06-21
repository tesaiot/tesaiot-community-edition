<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# การตรวจสอบการติดตั้ง

หลังรัน `make install` ใช้คู่มือนี้เพื่อยืนยันว่าทุก service ทำงานจริง และดูวิธีเข้าสู่ระบบ

## 1. เข้าสู่ระบบครั้งแรก

| | |
|---|---|
| **Admin UI** | `https://localhost/` (หรือ `https://<โดเมนของคุณ>/`) |
| **เข้าระบบด้วย** | **อีเมล** ที่อยู่ใน `ADMIN_EMAIL` (ค่าเริ่มต้น `admin@localhost`) |
| **รหัสผ่าน** | ค่าของ `ADMIN_PASSWORD` ใน `.env` ที่ถูกสร้างขึ้น |

ใบรับรอง TLS รอบแรกเป็นแบบ self-signed เบราว์เซอร์จะเตือนในครั้งแรก — กดยอมรับได้
(หรือเปลี่ยนเป็นใบรับรองจาก Vault PKI / Let's Encrypt ตาม [security-tls-mtls.md](security-tls-mtls.md))
แนะนำให้เปลี่ยนรหัสผ่าน admin จากใน UI หลังเข้าระบบครั้งแรก

> หน้า login ใช้ **อีเมล** ในการเข้าระบบ (ไม่ใช่ username)

### endpoint อื่น ๆ

| Service | URL | หมายเหตุ |
|---------|-----|----------|
| Admin UI + Telemetry Dashboard | `https://localhost/` | nginx :443 |
| REST API | `https://localhost/api/v1/` | `:5566` เป็น internal เท่านั้น |
| IoT mTLS telemetry ingest | `https://localhost:9444/` | |
| EMQX dashboard | `http://localhost:18083` | user `admin`; รหัส = `EMQX_DASHBOARD_PASSWORD` ใน `.env` |
| APISIX gateway | `http://localhost:9080` (admin `:9180`) | |
| Vault UI | `http://localhost:8200/ui` | token = `VAULT_ROOT_TOKEN` ใน `.env` |
| MQTT | `:8883` mTLS · `:8884` serverTLS · `:8083` WS · `:8084` WSS | |

## 2. ตรวจสุขภาพ (health check)

```bash
make health
```

ทุกแถวควรขึ้น `UP` และสรุปว่า `N up, 0 down`

## 3. ทดสอบ end-to-end (smoke test)

มี smoke test แบบครบในตัวที่ตรวจ **ทั้ง 11 containers พร้อมฟลo IoT จริง** —
login (JWT), สร้าง device, ingest telemetry, MQTT bridge, edge (nginx / APISIX),
broker (EMQX), Vault PKI และฐานข้อมูลทั้งสอง:

```bash
make smoke
# หรือ:  python3 scripts/smoke-test.py        (เพิ่ม -v เพื่อดูรายละเอียดทีละ check)
```

- อ่าน credentials/secret จาก `.env` อัตโนมัติ
- override admin ได้: `ADMIN_EMAIL=… ADMIN_PASSWORD=… python3 scripts/smoke-test.py`
- ใช้แค่ Python 3 standard library (ไม่ต้องลง package เพิ่ม)
- **exit code 0** = ผ่านทุก check (ใช้ใน CI ได้); **1** = มีอย่างน้อยหนึ่ง check ที่ fail

ผลลัพธ์ที่คาดหวัง:

```
SUMMARY: 28/28 checks passed, 0 failed
```

## 4. ตรวจทีละ service

```bash
# สถานะ container
docker compose ps

# Vault — initialised + unsealed
docker exec tesa-vault vault status

# MongoDB — replica set primary (-> 1)
docker exec tesa-mongodb mongosh --quiet --eval 'rs.status().myState'

# TimescaleDB — มี hypertable telemetry (-> 1)
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -tAc \
  "SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name='device_telemetry';"

# Redis (-> PONG)
docker exec tesa-redis sh -c 'redis-cli -a "$REDIS_PASSWORD" ping'

# API health (ผ่าน nginx)
curl -k https://localhost/api/v1/health

# EMQX broker
docker exec tesa-emqx emqx ctl status

# APISIX gateway
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:9080/
```

ถ้ามีอะไรไม่ healthy ดู [troubleshooting.md](troubleshooting.md)

## 5. API Keys ระดับองค์กร

เข้าระบบเป็น admin แล้วเปิดเมนู **API Keys** ในแถบข้าง เพื่อออก API key สำหรับ REST API /
gateway ใน Community Edition key เหล่านี้เก็บใน MongoDB และตรวจสอบที่ชั้น API
(APISIX ทำงานโหมด standalone YAML จึงไม่มี per-consumer key ที่ตัว gateway)
key จะแสดงเต็มครั้งเดียวตอนสร้าง/หมุน โดยเก็บเฉพาะ hash + prefix เท่านั้น ดู
[api-gateway-apisix.md](api-gateway-apisix.md)

key ระดับองค์กร (prefix `tesaiot_org_…`) ใช้ยืนยันตัวตนกับ API อ่านข้อมูลได้ จึงดึง
telemetry ของอุปกรณ์ผ่าน APISIX gateway ได้โดยตรง ไม่ต้องล็อกอินผ่านเบราว์เซอร์ ส่งเป็น
header `X-API-Key` (หรือ `?api_key=`):

```bash
# อ่าน telemetry ล่าสุดของอุปกรณ์ผ่าน gateway (:9443)
curl -k https://localhost:9443/api/v1/devices/<device_id>/telemetry/last \
  -H "X-API-Key: tesaiot_org_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

key เป็นสิทธิ์อ่านอย่างเดียวและจำกัดขอบเขตตามองค์กรของ key นั้น ถ้า key ผิดหรือถูกเพิกถอน
จะได้ `401`

## 6. ส่ง telemetry ผ่าน MQTT (serverTLS และ mTLS)

โหมดยืนยันตัวตนของอุปกรณ์ทั้งสองแบบ publish ไปที่ broker เดียวกันและลงที่ time-series store
สร้างอุปกรณ์ใน UI (หรือผ่าน API) แล้ว:

- **serverTLS (`:8884`)** — อุปกรณ์ยืนยันตัวตนด้วย **device id เป็น MQTT username** และ
  MQTT password ที่ระบบสร้างให้ ผ่านการเชื่อมต่อ TLS ที่ตรวจสอบใบรับรองของ broker
  publish JSON ไปที่ `device/<device_id>/telemetry`
- **mTLS (`:8883`)** — สร้างอุปกรณ์ด้วย `auth_mode: mtls` ออกใบรับรอง (Device →
  Certificate → *Generate/Renew* หรือ `POST /api/v1/devices/<id>/certificate/renew`)
  แล้วดาวน์โหลด client certificate + key (Vault PKI ออกใบรับรอง client แบบ EC P-256)
  อุปกรณ์ส่งใบรับรองนั้น broker ตรวจสอบตอน TLS handshake และ webhook ของ API อนุญาตจาก
  CN ของใบรับรอง โดยส่ง **device id เป็น MQTT username** ด้วย (ต้องตรงกับ CN ของใบรับรอง)

หลัง publish ตรวจได้จาก time-series tier:

```bash
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -tAc \
  "SELECT count(*) FROM telemetry_generic WHERE device_id='<device_id>';"
```

และผ่าน read API / gateway ตามข้อ 5

## 7. ตรวจสอบอิมเมจ pre-built (ลายเซ็น, SBOM, provenance)

อิมเมจทั้งสามที่ TESAIoT สร้างและเผยแพร่บน `ghcr.io/tesaiot/…` ถูก
**เซ็นแบบ keyless ด้วย [cosign](https://docs.sigstore.dev/)** และแนบ **SBOM** กับ
**SLSA build provenance** มาด้วย จึงพิสูจน์ได้ว่าอิมเมจถูก build โดย CI ของรีโปนี้จาก
source นี้จริง และไม่ถูกแก้ไขระหว่างทาง

```bash
# ตรวจสอบลายเซ็น (identity = release workflow ของรีโปนี้)
cosign verify ghcr.io/tesaiot/tesa-api:1.1.4 \
  --certificate-identity-regexp '^https://github.com/tesaiot/tesaiot-community-edition/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# ดู SBOM และ provenance ที่แนบมา
docker buildx imagetools inspect ghcr.io/tesaiot/tesa-api:1.1.4 \
  --format '{{ json .Provenance }}'
cosign download sbom ghcr.io/tesaiot/tesa-api:1.1.4
```

ทำซ้ำกับ `tesa-admin-ui` และ `tesa-mqtt-bridge` ถ้า `cosign verify` ล้มเหลว แปลว่า
อิมเมจไม่ใช่ build อย่างเป็นทางการ — อย่ารัน
