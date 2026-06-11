# การจัดการอุปกรณ์ / อัตลักษณ์

โมดูล Device / Identity Management ใช้ลงทะเบียน แสดงรายการ และจัดการอัตลักษณ์ของอุปกรณ์ IoT
ตลอดวงจรชีวิต รวมถึงการเชื่อมโยงใบรับรองและข้อมูลรับรองเข้ากับแต่ละอุปกรณ์

## ภาพรวม

โมดูลนี้อยู่ในโค้ด API ที่ `services/api/api/modules/device_management/` และ mount เข้ากับ
Flask monolith ผ่าน FastAPI ข้อมูลอุปกรณ์เก็บใน MongoDB

ทุกอุปกรณ์อยู่ในองค์กรเดียว (`DEFAULT_ORG_ID`) ตาม Community Edition

## วงจรชีวิตอุปกรณ์

```
ลงทะเบียน (register) -> provisioning (ออกใบรับรอง/credential) -> active
        -> ส่ง telemetry -> (เพิกถอน/ปลดระวาง) -> revoked / decommissioned
```

## การลงทะเบียนอุปกรณ์

จาก Admin UI:

1. login แล้วไปที่หน้า Devices
2. กด "Register Device" กรอกข้อมูล: ชื่อ/รหัสอุปกรณ์, ประเภท, โหมดยืนยันตัวตน (serverTLS หรือ mTLS)
3. ระบบสร้าง device identity และ (สำหรับ mTLS) ขอ Vault PKI ออกใบรับรองไคลเอนต์
4. รับข้อมูลสำหรับติดตั้งบนอุปกรณ์: ใบรับรอง + key + CA chain หรือ API key สำหรับ ingest ผ่าน HTTP

## โหมดยืนยันตัวตนของอุปกรณ์

| โหมด | ใช้สำหรับ | credential |
|---|---|---|
| **serverTLS** | อุปกรณ์เชื่อม MQTT พอร์ต 8884 หรือ HTTP ingest | username/password (MQTT) หรือ API key (HTTP) |
| **mTLS** | อุปกรณ์เชื่อม MQTT พอร์ต 8883 ด้วยใบรับรองไคลเอนต์ | client cert + key จาก Vault PKI |

ดูรายละเอียดโหมดได้ที่ [security-tls-mtls.md](security-tls-mtls.md)

## ข้อมูลรับรองสำหรับ ingest ผ่าน HTTP

อุปกรณ์ที่ส่ง telemetry ผ่าน HTTP ใช้ API key ที่ส่งใน header `X-API-Key` หรือ query
`?api_key=` ผ่าน APISIX gateway:

```
POST https://localhost:9443/api/v1/telemetry
X-API-Key: <device-api-key>
Content-Type: application/json

{"temperature": 25.4, "humidity": 60}
```

หรือแบบ device-scoped:

```
POST https://localhost:9443/api/v1/devices/<device-id>/telemetry
X-API-Key: <device-api-key>
```

API key ของอุปกรณ์ออกและตรวจสอบโดย API backend (`api_key_service.py`) — ไม่ได้ลงทะเบียนเป็น APISIX consumer ใน standalone YAML mode (ดู [api-gateway-apisix.md](api-gateway-apisix.md))

## การส่ง telemetry ผ่าน MQTT

อุปกรณ์ publish telemetry ไปยัง topic ที่ EMQX การยืนยันตัวตนและ ACL ตรวจผ่าน webhook ของ API
(ดู [mqtt-emqx.md](mqtt-emqx.md)) telemetry bridge จะรับและ forward เข้า API เพื่อเก็บลง
TimescaleDB/MongoDB

## การจัดการใบรับรองของอุปกรณ์

- ออกใบรับรองตอนลงทะเบียน (สำหรับ mTLS)
- ต่ออายุ — vault-agent ดูแลใบรับรองเซิร์ฟเวอร์ ส่วนใบรับรองอุปกรณ์ออกใหม่ผ่าน API
- เพิกถอน — เพิกถอนผ่าน Admin UI/API ซึ่งจะเพิ่ม serial เข้า CRL ของ Vault PKI

ดูรายละเอียดที่ [certificate-lifecycle.md](certificate-lifecycle.md)

## การดู telemetry ของอุปกรณ์

หน้า Device Details ของแต่ละอุปกรณ์ฝังแดชบอร์ด telemetry ที่ดึงข้อมูลอนุกรมเวลาจาก TimescaleDB
มาแสดงเป็นกราฟ ดู [telemetry-dashboard.md](telemetry-dashboard.md)

## ที่เก็บข้อมูล

- metadata อุปกรณ์ + ใบรับรอง: MongoDB (`tesa_iot`)
- telemetry: TimescaleDB (`tesa_telemetry`, hypertable) และ MongoDB เมื่อเปิด dual storage
  (`ENABLE_DUAL_STORAGE=true`)

## ดูเพิ่มเติม

- [certificate-lifecycle.md](certificate-lifecycle.md)
- [mqtt-emqx.md](mqtt-emqx.md)
- [telemetry-dashboard.md](telemetry-dashboard.md)
