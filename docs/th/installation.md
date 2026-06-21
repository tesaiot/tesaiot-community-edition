# การติดตั้ง

คู่มือนี้อธิบายการติดตั้ง TESAIoT Community Edition ตั้งแต่เครื่องเปล่าจนถึง stack ที่ทำงานได้สมบูรณ์

## ความต้องการของระบบ

| รายการ | ขั้นต่ำ | แนะนำ |
|---|---|---|
| ระบบปฏิบัติการ | Linux (x86_64) | Ubuntu 22.04 / 24.04 LTS |
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| พื้นที่ดิสก์ | 20 GB ว่าง | 50 GB+ (SSD) |
| Docker Engine | 24.x ขึ้นไป | เวอร์ชันล่าสุด |
| Docker Compose | v2 (ปลั๊กอิน) | v2 ล่าสุด |
| openssl | ติดตั้งแล้ว | ติดตั้งแล้ว |
| python3 | ติดตั้งแล้ว (generate-secrets.sh ใช้แพตช์ TLS/SNI ของ APISIX) | ติดตั้งแล้ว |

> ใช้ได้เฉพาะ Docker Compose **v2** (คำสั่ง `docker compose`) เท่านั้น
> ไม่รองรับ `docker-compose` รุ่นเก่า

ปริมาณ RAM/CPU ที่ stack ใช้ถูกกำหนดผ่าน resource limits ในแต่ละ service เช่น MongoDB และ
TimescaleDB จำกัดที่ 2G/2.0 CPU, API ที่ 2G/2.0 CPU

## รันบน macOS / Windows (Docker Desktop)

Stack นี้รันข้ามแพลตฟอร์มได้ ทั้งบน **Docker Desktop** (macOS ทั้ง Intel และ Apple Silicon,
และ Windows ที่ใช้ WSL 2) — image ทุกตัวเป็น multi-arch ดังนั้น Apple Silicon (arm64) จะดึง
image แบบ native อัตโนมัติ ข้อควรทราบสำหรับ Docker Desktop:

- **ตั้งหน่วยความจำให้พอ** — Docker Desktop → **Settings → Resources → Memory** ต้อง
  **อย่างน้อย 6 GB (แนะนำ 8 GB)** สำหรับ 11 services ค่าเริ่มต้น (มักเป็น 2–4 GB) ไม่พอ
  และ MongoDB/TimescaleDB อาจถูก OOM-killed
- **จุดที่เคยพังบน Docker Desktop ได้รับการแก้ในตัว distribution แล้ว** — ไม่ต้องทำ workaround เอง:
  - keyfile ของ MongoDB replica set จะถูก copy เข้า container แล้วแก้ permission ภายในตอนเริ่ม
    จึง**ไม่เกิด** error *"permissions on the keyfile are too open"* ที่ bind-mount keyfile มักทำให้
    เกิดบน macOS/Windows
  - สคริปต์ทั้งหมดเขียนให้รันได้ทั้งเครื่องมือ GNU (Linux) และ BSD (macOS) รวมถึง **bash 3.2**
    ที่มากับ macOS — เรียกด้วย `bash scripts/<ชื่อ>.sh` (หรือใช้ `make`)
- **`make`** มีอยู่แล้วบน macOS (ผ่าน Xcode Command Line Tools) และบน Windows ใช้ผ่าน
  WSL/Git Bash ได้ ถ้าไม่มีก็เรียกสคริปต์ตรง ๆ ได้
- นอกเหนือจากนี้เหมือน Linux ทุกประการ — Docker Desktop มี Docker Engine + Compose v2 ให้แล้ว
  ข้ามขั้นตอนติดตั้ง Docker ไปได้เลย

## ใช้โดเมนของคุณเอง (แหล่งความจริงแหล่งเดียว)

ถ้าจะ deploy บนโดเมนจริง (เช่น `iot.yourcompany.com`) แทน `localhost` ให้กำหนด
**ครั้งเดียว** ด้วยแฟล็ก `--domain` — **ไม่ต้อง**แก้ไฟล์ config ทีละไฟล์:

```bash
./scripts/generate-secrets.sh --domain=iot.yourcompany.com
make install
```

(หรือรวบเป็นคำสั่งเดียว: `make install DOMAIN=iot.yourcompany.com`)

ตัวแปร `DOMAIN` ใน `.env` คือ **แหล่งความจริงแหล่งเดียว** ของชื่อโฮสต์สาธารณะ
แฟล็ก `--domain` จะเขียนค่าลง `.env` และคำนวณค่าที่ขึ้นกับโฮสต์ใหม่ทั้งหมด ทำให้
ค่ากระจายไปทุกที่โดยไม่ต้องแก้หลายไฟล์:

- **CN/SAN ของใบรับรอง TLS** (ทั้ง self-signed ครั้งแรก และใบรับรองจาก Vault-PKI /
  EMQX ภายหลัง — `EMQX_CERT_CN`, `EMQX_CERT_ALT_NAMES`)
- **URL สาธารณะของ API / ingest / MQTT** ที่ประกาศให้อุปกรณ์
  (`TESA_PUBLIC_API_BASE_URL`, `TESA_PUBLIC_INGEST_BASE_URL`,
  `TESA_PUBLIC_MQTT_HOST`)
- **ชื่อโฮสต์สำหรับ onboarding** ที่ฝังใน device bundle, URL ลงทะเบียนแบบ QR และ
  ลิงก์ในอีเมล (`TESA_MQTT_DOMAIN`, `TESA_PROVISION_DOMAIN`, `TESA_ADMIN_DOMAIN`,
  `ADMIN_EMAIL`, `EMAIL_FROM_ADDRESS`, รวมถึงรายการ SNI ของ APISIX)

nginx ใช้ `server_name _` จึงตอบทุกโฮสต์อยู่แล้ว — ไม่ต้องแก้อะไรตรงนั้น

คำสั่งนี้ **idempotent และรันซ้ำได้อย่างปลอดภัย**: ติดตั้งบน `localhost` ก่อนแล้วค่อยรัน
`./scripts/generate-secrets.sh --domain=iot.yourcompany.com`
(หรือ `make set-domain DOMAIN=iot.yourcompany.com`) เพื่อเปลี่ยนภายหลังได้ — ค่าที่
คำนวณจาก `DOMAIN` จะถูกสร้างใหม่เสมอ ไม่มีค่าค้างเก่า จากนั้นใช้ `make restart`
(หรือรัน `make install` ซ้ำ) เพื่อให้มีผล

> **เงื่อนไข DNS:** ก่อนใช้งานจริง ต้องสร้าง DNS **A-record** (หรือ AAAA) ของโดเมน
> ให้ชี้มายัง IP สาธารณะของเครื่องนี้ อุปกรณ์และเบราว์เซอร์ต้อง resolve
> `iot.yourcompany.com` มาที่เซิร์ฟเวอร์ได้ TLS และ MQTT จึงจะทำงาน

คู่มือส่วนที่เหลือใช้ `localhost` เป็นตัวอย่าง ให้แทนที่ด้วยโดเมนของคุณตามที่ปรากฏ

## ติดตั้งด้วยคำสั่งเดียว (แนะนำ)

```bash
# ทางหลัก (เร็ว) — ดึงอิมเมจ pre-built แบบ multi-arch (amd64/arm64) จาก GHCR:
make install PREBUILT=1

# …หรือ build จาก source เอง (contributor / แก้โค้ด / ออฟไลน์):
make install
```

> **pre-built กับ build เอง:** มีเพียง 3 อิมเมจที่ TESAIoT สร้างเอง (`api`,
> `admin-ui`, `mqtt-bridge`) ซึ่งเผยแพร่ขึ้น `ghcr.io/tesaiot/…` ทุกครั้งที่ release
> เป็น public + multi-arch ส่วนที่เหลือเป็นอิมเมจจากต้นทาง `PREBUILT=1` จะดึง 3 อิมเมจ
> นี้แทนการ build และ **fallback ไป build เองอัตโนมัติ**ถ้าดึงไม่ได้ ทั้งสองทางได้ stack
> เหมือนกันเป๊ะ (ตั้ง `TESAIOT_REGISTRY` เพื่อใช้ mirror ได้)

(ไม่ต้อง `cp .env.example .env` เอง — สคริปต์จะสร้าง `.env` พร้อม secret สุ่มให้
การ copy ไฟล์ตัวอย่างที่ยังเป็น CHANGEME ไว้ก่อนจะทำให้ preflight ล้มเหลว)

หรือระบุโดเมนสาธารณะตั้งแต่ครั้งแรก (ทั้งสองทาง):

```bash
make install PREBUILT=1 DOMAIN=example.com
```

`make install` จะเรียก `scripts/install.sh` ซึ่งทำตามลำดับดังนี้:

1. **Preflight** — ตรวจสอบ Docker, พอร์ต, ดิสก์ และไฟล์ `.env`
2. **Secrets** — สร้าง `.env` พร้อม secret แบบสุ่ม, mongo keyfile และใบรับรอง TLS แบบ self-signed สำหรับใช้ครั้งแรก
3. **Infra** — ยก Vault และฐานข้อมูลขึ้น
4. **Vault PKI** — initialise + unseal Vault และสร้างลำดับชั้น PKI (pki-root → pki-int)
5. **DB init** — ตั้งค่า MongoDB replica set และตรวจสอบ TimescaleDB hypertable
6. **Restart** — restart service ที่ต้องใช้ใบรับรอง
7. **App** — ยก API, admin-ui, nginx ขึ้น
8. **EMQX + APISIX** — provision broker auth และ sync admin key
9. **Health** — ตรวจสุขภาพทุก service

สคริปต์นี้ปลอดภัยที่จะรันซ้ำ (idempotent)

## ติดตั้งทีละขั้น (manual)

หากต้องการควบคุมแต่ละขั้น สามารถเรียก make target แยกได้:

**ลำดับสำคัญ**: ต้องยก Vault ขึ้นและรัน `make init-pki` ก่อนยก stack ที่เหลือ
(vault-agent ต้องรอ AppRole credential ที่ init-pki เป็นคนสร้าง ไม่เช่นนั้น
`depends_on` ของ api จะไม่มีวันผ่าน):

```bash
make preflight              # ตรวจสอบ prerequisite ของ host
make secrets                # สร้าง .env, mongo keyfile, TLS certs + render config templates
make build                  # build อิมเมจจาก source  (หรือ: make pull — ดึงอิมเมจ pre-built จาก GHCR)
docker compose up -d vault  # ยก Vault ขึ้นก่อน
make init-pki               # initialise/unseal Vault และสร้าง PKI
make up                     # ยก stack ที่เหลือขึ้นทั้งหมด
make init-db                # ตั้งค่า MongoDB replica set + ตรวจ TimescaleDB
make init-emqx              # provision broker auth (internal bridge user)
make init-apisix            # sync admin key + ตรวจสอบ route ของ APISIX
make health                 # ตรวจสุขภาพและพิมพ์ตารางสถานะ
```

## ตรวจสอบการติดตั้ง

```bash
make ps        # แสดงสถานะ container
make health    # ตรวจสุขภาพทุก service
make smoke     # ทดสอบ end-to-end (login → device → telemetry → MQTT → gateway)
make logs      # ดู log ทั้งหมด (หรือ make logs s=api สำหรับ service เดียว)
```

`make health` เรียก `scripts/healthcheck.sh` ซึ่งจะ probe แต่ละ service และพิมพ์ตาราง
UP / WARN / DOWN ส่วน `make smoke` รัน `scripts/smoke-test.py` ทดสอบครบทั้ง 11 containers
และฟลo IoT จริง (ควรได้ `SUMMARY: 28/28 checks passed, 0 failed`) — ดูเพิ่มเติมที่
[verification.md](verification.md)

## จุดเข้าใช้งานหลังติดตั้ง

| บริการ | URL | หมายเหตุ |
|---|---|---|
| Admin UI + API | `https://localhost` | ผ่าน nginx (พอร์ต 443) |
| Telemetry ingest | `https://localhost:9444` | ช่องทาง ingest แยก |
| API โดยตรง | (ไม่ถูก publish บน host) | :5566 เป็น internal-only — เข้าผ่าน nginx เท่านั้น |
| EMQX dashboard | `http://localhost:18083` | รหัสผ่านจาก `EMQX_DASHBOARD_PASSWORD` |
| Vault UI | `http://localhost:8200` | token จาก `VAULT_ROOT_TOKEN` |
| APISIX gateway | `http://localhost:9080` / `https://localhost:9443` | |

ผู้ดูแลระบบเริ่มต้น (bootstrap admin) ถูกสร้างจากตัวแปร `ADMIN_EMAIL`, `ADMIN_USERNAME`,
`ADMIN_PASSWORD` ใน `.env`

## พอร์ตที่เปิดสู่ภายนอก

```
80, 443, 9444     nginx  (HTTP, HTTPS, ingest)
8883              MQTT mTLS
8884              MQTT serverTLS
8084              MQTT over WebSocket (WSS)
9443              APISIX (https)
-- loopback เท่านั้น (127.0.0.1 ไม่ออก LAN) --
8200              Vault
1883, 8083        MQTT plain / WS (local/dev)
18083             EMQX dashboard
9080, 9180        APISIX (http, admin API)
```

API (5566) และ MongoDB (27017) ไม่ถูก publish บน host เลย — เข้าถึงได้เฉพาะใน
เครือข่ายภายในของ Docker ส่วนพอร์ตจัดการ (8200, 9180, 18083, 1883) ถูก bind ไว้ที่
loopback อยู่แล้วจึงไม่ออกอินเทอร์เน็ตโดยตรง

## ขั้นถัดไป

- ปรับแต่งค่าได้ที่ [configuration.md](configuration.md)
- ตั้งค่า TLS/mTLS สำหรับ production ที่ [security-tls-mtls.md](security-tls-mtls.md)
- หากพบปัญหา ดู [troubleshooting.md](troubleshooting.md)
