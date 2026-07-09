# TESA IoT Device → Platform (mTLS) — HTTPS หรือ MQTTS ผ่าน Mongoose

> **ภาษาไทย** - สำหรับเวอร์ชันภาษาอังกฤษ ดูที่ [README.md](README.md)

ตัวอย่างภาษา C แบบ unified สำหรับผู้เริ่มต้น สามารถส่ง telemetry ได้ทั้ง:
- HTTPS mTLS (client certificate + private key)
- MQTTS mTLS (client certificate + private key)

ใช้ไลบรารี Cesanta Mongoose แบบ single-file รองรับ TLS backends: OpenSSL, mbedTLS, หรือ wolfSSL

> Licensing: ทุกไฟล์ C/Python/shell ในตัวอย่างนี้ใช้ Apache 2.0 license
> (`Copyright (c) 2025 TESAIoT Platform (TESA)`) สามารถนำไปปรับใช้ในโปรเจกต์ lab ได้ตามสะดวก

---

## สรุปเริ่มต้นเร็ว

- ดาวน์โหลดบันเดิล mTLS จาก Admin UI → Credentials
- รัน `make prepare` เพื่อซิงค์ไฟล์มายัง `./certs_credentials`
- รันทดสอบ 2 นาที (ส่งทุก 10 วินาที):
  - HTTPS: `COMM_MODE=HTTPS API_BASE_URL=https://localhost:9444 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - MQTTS: `COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8883 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`

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

- ดาวน์โหลด Device01 mTLS bundle จาก Admin UI → Credentials → "Download mTLS bundle"
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

## รัน — HTTPS (mTLS)

```bash
COMM_MODE=HTTPS \
API_BASE_URL=https://localhost:9444 \
CERTS_DIR=./certs_credentials \
./device_client
```

## รัน — MQTTS (mTLS)

```bash
COMM_MODE=MQTTS \
MQTT_HOST=localhost MQTT_PORT=8883 \
CERTS_DIR=./certs_credentials \
./device_client
```

## พฤติกรรม

- สร้าง JSON `{device_id, timestamp, data}` โดยอ่านโครงสร้างฟิลด์จากไฟล์ schema หากมี
  - ค้นหาอัตโนมัติที่ `../download/data_schema.txt` (หรือกำหนดด้วย `SCHEMA_PATH`)
  - รองรับชนิด `integer/number/string/boolean` พร้อม minimum/maximum และ `enum` (เลือกค่าตัวแรก)
  - หากไม่พบไฟล์ schema จะ fallback เป็นฟิลด์ตัวอย่างเดิม
- การยืนยัน TLS บังคับเปิดเสมอ ห้ามปิด SSL พาธอ่านจาก `CERTS_DIR/`
- อ่าน `endpoints.json` หากมีและใช้ `api_base_url` หรือ `ingest_base_url`
- Device ID อ่านจาก `device_id.txt` หรือกำหนดทับด้วย env var `DEVICE_ID`

## องค์ความรู้

- โครงสร้าง payload แบบ schema-driven: โปรแกรมอ่านสคีมาจาก `../download/data_schema.txt` (หรือ `SCHEMA_PATH`) แล้วสร้างค่าแบบสุ่มที่สอดคล้องกับข้อกำหนดของแต่ละฟิลด์ (range/enum/type) เพื่อให้การทดสอบสะท้อนรูปแบบข้อมูลจริง
- การจับคู่พอร์ต: mTLS → HTTPS ใช้ 9444, MQTTS ใช้ 8883 ตามการออกแบบของแพลตฟอร์ม เพื่อลดโอกาสผิดพลาดเรื่อง SAN/ALPN และนโยบายความปลอดภัย
- Trust model: การยืนยันฝั่ง TLS ใช้ system trust ของเครื่องเพื่อเชื่อถือ `tesaiot.com` ไม่ควรวาง CA ผิดโดเมนทับซ้อน (หลีกเลี่ยง CA ที่ไม่เกี่ยวข้อง)
- CSR device: ตามหลักการความปลอดภัย bundle ที่สร้างจาก CSR จะไม่มี private key ใน ZIP จำเป็นต้องวางกุญแจที่ผลิตจากฝั่งอุปกรณ์ลง `certs_credentials/client_key.pem` ก่อนใช้งาน

## การแก้ปัญหา (Troubleshooting)

- TLS Handshake สำเร็จแต่ส่งไม่ผ่าน (HTTPS 4xx): ตรวจ `X-API-KEY` สำหรับโหมด serverTLS (mTLS ไม่ใช้ API key), ตรวจเวลาระบบ/รูปแบบ timestamp ตามสคีมา
- mTLS ขึ้น error ว่าไม่มี private key: รัน `./scripts/sync_csr_key.sh <DEVICE_ID>` เพื่อคัดลอกจาก `./csr/`
- SAN/โดเมนไม่ตรง: ตรวจว่าคุณใช้ `https://localhost:9444` สำหรับ ingest mTLS (ไม่ใช้พอร์ต 443)
- ข้อมูลไม่ตรงสคีมา: กำหนด `SCHEMA_PATH=/path/to/data_schema.txt` เพื่อชี้ไฟล์สคีมาที่ต้องการ

## หัวข้อขั้นสูง

- ตัวแปรสำคัญ:
  - `COMM_MODE`, `API_BASE_URL`, `MQTT_HOST`, `MQTT_PORT`, `CERTS_DIR`, `SCHEMA_PATH`, `TLS_BACKEND`
  - ปรับความถี่ส่งด้วย `--period` และ `--interval`

- หมายเหตุการใช้งานข้ามแพลตฟอร์ม:
  - Linux / Raspberry Pi: ติดตั้งแพ็กเกจพัฒนาให้ครบ (ดู Build)
  - macOS: ใช้ Homebrew OpenSSL และตั้งค่า CPPFLAGS/LDFLAGS หากระบบหาไม่เจออัตโนมัติ

## Legacy Clients (ไม่บังคับ)

- ดู `./c/` สำหรับตัวส่งแบบ libmosquitto/libcurl อย่างง่าย (เก็บไว้เพื่อเปรียบเทียบ) ค่าเริ่มต้นใช้ Mongoose

## CLI Flags

- `--mode HTTPS|MQTTS`: บังคับโหมด transport, override env `COMM_MODE`
- `--host <host>` และ `--port <n>`: override MQTT host/port (MQTTS) หรือ base host/port (HTTPS เมื่อใช้ร่วมกับ `API_BASE_URL`)
- `--period <minutes>`: ระยะเวลาส่งทั้งหมดเป็นนาที
- `--interval <seconds>`: ช่วงห่างของการส่งเป็นวินาที

## ผลทดสอบ (2025-09-15) — รัน 2 นาที

- HTTPS mTLS: OK. ส่ง telemetry ทุก 10 วินาที นาน 2 นาที
  - คำสั่ง: `COMM_MODE=HTTPS API_BASE_URL=https://localhost:9444 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - หมายเหตุ: ใช้ client cert/key; TLS verification ผ่าน system trust (public CA) สำเร็จ
- MQTTS mTLS (port 8883): OK. ส่งทุก 10 วินาที นาน 2 นาที
  - คำสั่ง: `COMM_MODE=MQTTS CERTS_DIR=./certs_credentials ./device_client --host localhost --port 8883 --period 2 --interval 10`
  - หมายเหตุ: TLS handshake และ PUBACK received (QoS1) ทุกรอบ

## ข้อแนะนำ

- สำหรับ HTTPS mTLS: ไม่ต้องทำอะไรเพิ่มเติม; config ปัจจุบันทำงานได้กับ system trust สำหรับ tesaiot.com
- สำหรับ MQTTS mTLS: ตรวจสอบให้แน่ใจว่า client certificate ของอุปกรณ์ได้รับอนุญาตบน broker และ broker map client cert ไปยังสิทธิ์สำหรับ topic `device/<device_id>/telemetry`

## เคล็ดลับ Schema

- ไฟล์ schema ใช้ตามตัวอย่าง `download/data_schema.txt` (JSON Schema แบบเรียบง่าย)
- หากเป็น CSR device ให้ซิงค์ private key ไปที่ `certs_credentials/client_key.pem` ก่อนใช้งาน mTLS
  - สคริปต์ช่วย: `./scripts/sync_csr_key.sh <DEVICE_ID>`
