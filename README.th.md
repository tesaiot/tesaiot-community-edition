# TESAIoT Community Edition

> เอกสารฉบับภาษาไทย — ดูฉบับภาษาอังกฤษได้ที่ [`README.md`](README.md)

**TESAIoT Community Edition** เป็นชุดแจกจ่าย (distribution) แบบโอเพนซอร์สภายใต้สัญญาอนุญาต
Apache-2.0 สำหรับการติดตั้งใช้งานเอง (self-host) ในรูปแบบ **องค์กรเดียว (single-organization)**
โดยสกัดมาจาก TESAIoT Secure IoT Platform ฉบับเต็ม เป้าหมายคือให้ทีมขนาดเล็กสามารถยกแพลตฟอร์ม
IoT ที่ปลอดภัยขึ้นมาใช้งานได้ด้วยคำสั่งเดียว บนเครื่องเดียว โดยไม่ต้องพึ่งพาบริการคลาวด์ภายนอก

## ความสามารถในขอบเขต (8 ด้าน)

1. **การจัดการผู้ใช้ (User Management)** — บัญชีผู้ใช้ภายใน บทบาท และการยืนยันตัวตนสำหรับองค์กรเดียว
2. **การจัดการอุปกรณ์ / อัตลักษณ์ (Device / Identity Management)** — ลงทะเบียน แสดงรายการ และจัดการอัตลักษณ์ของอุปกรณ์ IoT ตลอดวงจรชีวิต
3. **โหมดยืนยันตัวตน serverTLS และ mTLS** — รองรับทั้ง TLS ฝั่งเซิร์ฟเวอร์ และ mutual-TLS สำหรับอุปกรณ์
4. **การจัดการวงจรชีวิตใบรับรอง (Certificate Life-cycle)** — ออก ต่ออายุ และเพิกถอนใบรับรองผ่าน HashiCorp Vault PKI
5. **APISIX API Gateway** — เกตเวย์ขอบสำหรับจัดเส้นทางและป้องกัน API ของแพลตฟอร์ม
6. **EMQX MQTT Broker** — โบรกเกอร์ MQTT สำหรับรับ telemetry และคำสั่งควบคุมจากอุปกรณ์
7. **MongoDB และ TimescaleDB** — MongoDB สำหรับข้อมูลเอกสาร/เมทาดาทา และ TimescaleDB สำหรับข้อมูลอนุกรมเวลา
8. **แดชบอร์ด Telemetry** — กราฟ telemetry ที่ฝังอยู่ในหน้า Device Details

## สิ่งที่ไม่รวมอยู่ในชุดนี้

multi-tenancy / หลายองค์กร, AI inference, Flowise, OTA / firmware update, virtual-ota-server,
WebSocket B2B, cpp-ml-service, third-party services (BENTO IDE, Developer Hub, summit sites),
โมดูล analytics และ stack มอนิเตอร์ Grafana/Prometheus

## สถาปัตยกรรมโดยย่อ

stack ประกอบด้วย 11 services ที่จัดการผ่าน Docker Compose:

| Service | อิมเมจ | บทบาท | พอร์ตที่เผยแพร่ |
|---|---|---|---|
| `vault` | hashicorp/vault:1.18.3 | PKI + secrets engine | 8200 |
| `vault-agent` | hashicorp/vault:1.18.3 | render/ต่ออายุใบรับรองอัตโนมัติ | — |
| `mongodb` | mongo:8.0 | ทะเบียนผู้ใช้/อุปกรณ์/ใบรับรอง | — (ภายใน) |
| `timescaledb` | timescale/timescaledb:2.17.2-pg14 | telemetry time-series | — (ภายใน) |
| `redis` | redis:7.4.4-alpine | cache + rate-limit | — (ภายใน) |
| `api` | tesa-api | API หลัก (Flask + FastAPI) | 5566 |
| `admin-ui` | tesa-admin-ui | React SPA (nginx) | — (ภายใน) |
| `emqx` | emqx/emqx:5.10.0 | MQTT broker | 1883, 8883, 8884, 8083, 8084, 18083 |
| `mqtt-bridge` | tesa-mqtt-bridge | สะพาน telemetry EMQX → API | — |
| `nginx` | nginx:1.27.5-alpine | TLS termination + reverse proxy | 80, 443, 9444 |
| `apisix` | apache/apisix:3.11.0-debian | API gateway (standalone YAML) | 9080, 9443, 9180 |

> APISIX ทำงานในโหมด standalone YAML จึง **ไม่ต้องใช้ etcd**

## เริ่มต้นอย่างรวดเร็ว

ต้องมี Docker Engine + Docker Compose v2, `openssl`, `python3`, `curl` รันได้ทั้งบน
Linux และบน **Docker Desktop** (macOS ทั้ง Intel และ Apple Silicon รวมถึง Windows/WSL 2)
อิมเมจทั้งหมดเป็น multi-arch

```bash
cp .env.example .env
make install
```

`make install` จะรันลำดับ: preflight → secrets → vault/databases → Vault PKI →
db init → restart services ที่ต้องใช้ใบรับรอง → ยก app ขึ้น → emqx + apisix → health

หลังติดตั้งเสร็จ:

- Admin UI / API: `https://localhost` (ผ่าน nginx) — เข้าระบบด้วย `ADMIN_EMAIL` / `ADMIN_PASSWORD` จาก `.env`
- EMQX dashboard: `http://localhost:18083`
- Vault UI: `http://localhost:8200`

ตรวจสอบว่าทุก service ทำงานครบด้วย:

```bash
make health      # ตารางสถานะ 11 services
make smoke       # ทดสอบ end-to-end (login → device → telemetry → MQTT → gateway)
```

อ่านรายละเอียดทั้งหมดได้ใน [`docs/th/installation.md`](docs/th/installation.md) และ
[`docs/th/verification.md`](docs/th/verification.md)

## ภาพหน้าจอ (Screens)

ทัวร์หน้าจอ Admin UI โดยย่อ (Community Edition แบบองค์กรเดียว)

### แดชบอร์ด (Operational Overview)
ภาพรวมเรียลไทม์ของอัตรา telemetry, ความเสถียรของแพลตฟอร์ม และสถานะความปลอดภัย

![Dashboard](docs/images/screenshots/screen-dashboard.png)

### Devices & Identity
ลงทะเบียนอุปกรณ์และผูกกับอัตลักษณ์ X.509 จริง เลือกโหมด **serverTLS** หรือ **mTLS**

![Devices](docs/images/screenshots/screen-devices.png)

### Certificates
ออก / ต่ออายุ / เพิกถอนใบรับรองอุปกรณ์และบริการจาก Vault PKI สองชั้น

![Certificates](docs/images/screenshots/screen-certificates.png)

### API Keys (Developer Access)
ออก กำหนดสิทธิ์ หมุน และเพิกถอน API key ระดับองค์กรสำหรับ REST API / gateway
(เก็บเป็น hash + prefix แสดงเต็มครั้งเดียวตอนสร้าง)

![API Keys](docs/images/screenshots/screen-api-keys.png)

### Compliance
สถานะมาตรฐานความปลอดภัยของระบบ — ETSI EN 303 645 และ ISO/IEC 27402 (~70% baseline
ที่ CE ครอบคลุมในชั้นแพลตฟอร์ม) พร้อมเปิดเผยส่วนที่เป็นความรับผิดชอบของผู้ดูแล/แผนงานอย่างตรงไปตรงมา

![Compliance](docs/images/screenshots/screen-compliance.png)

## เอกสาร (ภาษาไทย)

- [การติดตั้ง (installation.md)](docs/th/installation.md)
- [การตรวจสอบการทำงาน (verification.md)](docs/th/verification.md)
- [การตั้งค่า (configuration.md)](docs/th/configuration.md)
- [สถาปัตยกรรม (architecture.md)](docs/th/architecture.md)
- [ความปลอดภัย TLS/mTLS (security-tls-mtls.md)](docs/th/security-tls-mtls.md)
- [วงจรชีวิตใบรับรอง (certificate-lifecycle.md)](docs/th/certificate-lifecycle.md)
- [การจัดการผู้ใช้ (user-management.md)](docs/th/user-management.md)
- [การจัดการอุปกรณ์ (device-management.md)](docs/th/device-management.md)
- [API Gateway / APISIX (api-gateway-apisix.md)](docs/th/api-gateway-apisix.md)
- [MQTT / EMQX (mqtt-emqx.md)](docs/th/mqtt-emqx.md)
- [แดชบอร์ด Telemetry (telemetry-dashboard.md)](docs/th/telemetry-dashboard.md)
- [สำรอง/กู้คืนข้อมูล (backup-restore.md)](docs/th/backup-restore.md)
- [การแก้ปัญหา (troubleshooting.md)](docs/th/troubleshooting.md)
- [การอัปเกรด (upgrade.md)](docs/th/upgrade.md)

## สัญญาอนุญาต

เผยแพร่ภายใต้ Apache License 2.0 ดู [`LICENSE`](LICENSE) และ [`NOTICE`](NOTICE)
