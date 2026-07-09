# TESA IoT Device → Platform (Server-TLS) — HTTPS หรือ MQTTS ผ่าน Mongoose

> **ภาษาไทย** - สำหรับเวอร์ชันภาษาอังกฤษ ดูที่ [README.md](README.md)

ตัวอย่างภาษา C แบบ unified สำหรับผู้เริ่มต้น สามารถส่ง telemetry ได้ทั้ง:
- HTTPS Server-TLS (API key + CA)
- MQTTS Server-TLS (username/password + CA)

ใช้ไลบรารี Cesanta Mongoose แบบ single-file รองรับ TLS backends: OpenSSL, mbedTLS, หรือ wolfSSL

> Licensing: ทุก source helper ในโฟลเดอร์นี้ใช้ Apache 2.0 header
> (`Copyright (c) 2025 TESAIoT Platform (TESA)`) สามารถนำไปใช้ในโปรเจกต์ lab ได้อย่างปลอดภัย

---

## สรุปเริ่มต้นเร็ว

- ดาวน์โหลด Server-TLS bundles จาก Admin UI (เลือก include_password/include_api_key เมื่อจำเป็น)
- รัน `make prepare` เพื่อซิงค์ให้ตรงกับฐานข้อมูล
- รันทดสอบ 2 นาที (ส่งทุก 10 วินาที):
  - HTTPS: `COMM_MODE=HTTPS API_BASE_URL=https://localhost CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - MQTTS: `COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8884 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`

## โครงสร้างไดเรกทอรี

```text
.
├── scripts/
│   └── sync_credentials.sh
├── config.h
├── data_schema.c
├── data_schema.h
├── main.c                   # เลือก HTTPS หรือ MQTTS ผ่าน env COMM_MODE
├── Makefile                 # portable, ดาวน์โหลด Mongoose อัตโนมัติ
├── README.md
├── README-TH.md
├── certs_credentials/       # วาง bundle ที่ดาวน์โหลดมาไว้ที่นี่
└── ../common-c/             # shared Mongoose client (ดาวน์โหลดอัตโนมัติ)
```

## Credentials

- ดาวน์โหลด Device02 Server-TLS bundle จาก Admin UI → Credentials → "Download Server-TLS bundle"
- จากนั้น:

```bash
make prepare
```

## ติดตั้งไลบรารี

- Makefile จะดาวน์โหลด Mongoose ไปไว้ที่ `../common-c/` ให้อัตโนมัติเมื่อ build ครั้งแรก
- รองรับ TLS backend: OpenSSL (ค่าเริ่มต้น), mbedTLS, wolfSSL กำหนดด้วย `TLS_BACKEND=...`
- ติดตั้งแพ็กเกจตามระบบปฏิบัติการ:
  - Debian/Ubuntu (รวมถึง Raspberry Pi):
    - OpenSSL: `sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev`
    - mbedTLS: `sudo apt-get install -y build-essential pkg-config libmbedtls-dev`
    - wolfSSL: `sudo apt-get install -y build-essential pkg-config libwolfssl-dev`
  - macOS (Homebrew): `brew install openssl@3` และตั้งค่า `CPPFLAGS/LDFLAGS` หากระบบหาไม่เจออัตโนมัติ
- คำสั่ง build:
```bash
# ค่าเริ่มต้น: OpenSSL backend
make

# เลือก TLS backend
make TLS_BACKEND=mbedtls
make TLS_BACKEND=wolfssl

# แสดงคำแนะนำติดตั้ง dependencies สำหรับ OS ของคุณ
make deps
```

## รัน — HTTPS (Server-TLS)

```bash
COMM_MODE=HTTPS \
API_BASE_URL=https://localhost \
CERTS_DIR=./certs_credentials \
./device_client
```

## รัน — MQTTS (Server-TLS)

```bash
COMM_MODE=MQTTS \
MQTT_HOST=localhost MQTT_PORT=8884 \
CERTS_DIR=./certs_credentials \
./device_client
```

## พฤติกรรม

- สร้าง JSON `{device_id, timestamp, data}` โดยอ่านโครงสร้างฟิลด์จากไฟล์ schema หากมี
  - ค้นหาอัตโนมัติที่ `../download/data_schema.txt` (หรือกำหนดด้วย `SCHEMA_PATH`)
  - รองรับชนิด `integer/number/string/boolean` พร้อม minimum/maximum และ `enum` (เลือกค่าตัวแรก)
  - หากไม่พบไฟล์ schema จะ fallback เป็นฟิลด์ตัวอย่างเดิม
- HTTPS ใช้เฉพาะ `X-API-KEY: <api_key.txt>` (ไม่ต้องส่ง Bearer)
- การยืนยัน TLS บังคับเปิดเสมอ ห้ามปิด SSL พาธอ่านจาก `CERTS_DIR/`
- อ่าน `endpoints.json` หากมีและใช้ `api_base_url` หรือ `ingest_base_url`; ยังอ่าน `mqtt_host` และ `mqtt_tls_port` หากมี
- Device ID อ่านจาก `device_id.txt` หรือกำหนดทับด้วย env var `DEVICE_ID`

## องค์ความรู้

- โครงสร้าง payload แบบ schema-driven: โปรแกรมอ่านสคีมาจาก `../download/data_schema.txt` (หรือ `SCHEMA_PATH`) และสุ่มค่าให้สอดคล้องกับ type/min-max/enum ช่วยให้ทดสอบกับข้อมูลจริงได้รวดเร็ว
- การเลือกพอร์ต: serverTLS (user/pass) → MQTT ใช้ 8884, HTTPS ใช้ 443; mTLS แยกไป 8883/9444 ตามนโยบาย แยกเส้นทางชัดเจนลดความสับสน
- การยืนยันสิทธิ์: HTTPS ใช้เฉพาะ `X-API-KEY`, MQTTS ใช้ `username=device_id` และ `password` จาก bundle ที่ include_password=true เท่านั้น และ backend จะตรวจ hash ในฐานข้อมูล
- ACL โทปิค: อนุญาตเฉพาะ `device/<device_id>/telemetry` สำหรับ publish (subscribe ใช้ `device/<device_id>/commands|config|firmware`)

## การแก้ปัญหา (Troubleshooting)

- HTTPS 401: API key ไม่อัปเดต → ดาวน์โหลด HTTPS bundle ใหม่แบบ include_api_key=true แล้วรัน `./scripts/sync_credentials.sh --device-dir ../download`
- MQTTS Code 5 (Not authorized): username ไม่ตรงกับ device_id หรือ password หมดอายุ/ยังไม่ได้รีเซ็ต → ดาวน์โหลด MQTT Server-TLS bundle แบบ include_password=true แล้วซิงค์ใหม่
- พอร์ตสลับกับ mTLS: ถ้าไป 8883 จะเจอ TLS ปิด connection หลัง CONNECT เพราะโหมดไม่ตรง → ใช้ 8884 สำหรับ serverTLS
- ACL deny: ตรวจว่า topic เป็น `device/<device_id>/telemetry` และ client_id ตรงกับ `<device_id>`

## Legacy Clients (ไม่บังคับ)

- ดู `./c/` สำหรับตัวส่งแบบ libmosquitto/libcurl อย่างง่าย (เก็บไว้เพื่อเปรียบเทียบ) ค่าเริ่มต้นใช้ Mongoose

## ผลทดสอบ (2025-09-15) — รัน 2 นาที

- HTTPS Server-TLS: OK. ส่งสำเร็จทุก 10 วินาทีในช่วง 2 นาที (ต้องแน่ใจว่า `api_key.txt` เป็นชุดล่าสุดจาก HTTPS bundle)
- MQTTS Server-TLS (port 8884): OK. ส่งสำเร็จทุก 10 วินาทีในช่วง 2 นาที (หลังซิงค์รหัสผ่านใหม่จาก bundle)

## หมายเหตุ

- หากต้องการใช้ MQTTS แบบ Server-TLS ต้องมั่นใจว่า `mqtt_username.txt` และ `mqtt_password.txt` ถูกต้องสำหรับอุปกรณ์นี้ และ ACL อนุญาต publish ไปที่ `device/<device_id>/telemetry` บนพอร์ต 8884
- การยืนยัน TLS เปิดใช้งานตลอดเวลา; ไม่มีการลดความปลอดภัย SSL

## เคล็ดลับ Schema

- วาง `download/data_schema.txt` ไว้ที่โฟลเดอร์ตัวอย่าง หรือกำหนด `SCHEMA_PATH` ให้โปรแกรมอ่าน
- หาก HTTPS 401 ให้กดดาวน์โหลด HTTPS Server-TLS bundle ใหม่โดยเลือก include_api_key=true แล้วรันสคริปต์ซิงค์อีกครั้ง:
  - `./scripts/sync_credentials.sh --device-dir ../download`
