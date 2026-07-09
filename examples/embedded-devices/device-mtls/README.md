# TESA IoT Device → Platform (mTLS) — HTTPS or MQTTS via Mongoose

Unified, intermediate-level C example that can send telemetry over either:
- **HTTPS mTLS** (client certificate + private key)
- **MQTTS mTLS** (client certificate + private key)

Uses Cesanta Mongoose single-file library with TLS backends: OpenSSL, mbedTLS, or wolfSSL.

## Prerequisites

| Item | Description |
|------|-------------|
| GCC/Clang | C compiler with C11 support |
| OpenSSL/mbedTLS/wolfSSL | TLS library |
| Credentials | mTLS bundle from TESAIoT Platform |

## Getting Credentials from TESAIoT Platform

### Step 1: Download mTLS Bundle

1. Login to **TESAIoT Admin Portal**: https://admin.tesaiot.com
2. Navigate to **Devices** > Select your device
3. Go to the **Credentials** tab
4. Click **Download mTLS Bundle** (MQTT or HTTPS)
5. Extract the bundle to get:
   - `ca-chain.pem` - CA certificate chain
   - `<device-id>-certificate.pem` - Client certificate
   - `endpoints.json` - Connection endpoints

### Step 2: Sync Credentials

```bash
# Sync credentials to certs_credentials folder
make prepare
# Or manually:
./scripts/sync_credentials.sh --device-dir ../download
```

### Step 3: Sync Private Key (CSR Devices)

For CSR-based devices, the private key is NOT included in the bundle (security requirement). Copy it manually:

```bash
# Copy private key from CSR generation
./scripts/sync_csr_key.sh <DEVICE_ID>
```

### Step 4: Shared Credentials (Alternative)

Store in shared credentials folder:
```bash
cp -r /path/to/downloaded/bundle/* ../../shared/devices_credentials/<device-name>/
```

> **Note**: The `examples/shared/devices_credentials/` folder is for storing downloaded credentials. This folder is NOT committed to git repositories.

---

## Quick Start (EN)
- Download mTLS bundles in Admin UI → Credentials
- `make prepare` to sync credentials into `./certs_credentials`
- Run for 2 minutes (every 10s):
  - HTTPS: `COMM_MODE=HTTPS API_BASE_URL=https://localhost:9444 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - MQTTS: `COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8883 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`

สรุปเริ่มต้นเร็ว (TH)
- ดาวน์โหลดบันเดิล mTLS จาก Admin UI → Credentials
- รัน `make prepare` เพื่อซิงค์ไฟล์มายัง `./certs_credentials`
- รันทดสอบ 2 นาที (ส่งทุก 10 วินาที):
  - HTTPS: คำสั่งเดียวกับด้านบน
  - MQTTS: คำสั่งเดียวกับด้านบน

Directory Structure

```text
.
├── scripts/
│   └── sync_credentials.sh
├── config.h
├── data_schema.c
├── data_schema.h
├── main.c                   # selects HTTPS or MQTTS via env COMM_MODE
├── Makefile                 # portable, fetches Mongoose on demand
├── README.md
├── certs_credentials/       # place downloaded bundle here
└── ../common-c/             # shared Mongoose client (auto-downloaded)
```

Credentials

- Get Device01 mTLS bundle from Admin UI → Credentials → “Download mTLS bundle”.
- Then:

```bash
make prepare
```

Build / ติดตั้งไลบรารี

English
- The Makefile auto-fetches Mongoose into `../common-c/` on first build.
- TLS backends supported: OpenSSL (default), mbedTLS, wolfSSL. Pick with `TLS_BACKEND=...`.
- Install system deps per OS:
  - Debian/Ubuntu (incl. Raspberry Pi):
    - OpenSSL: `sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev`
    - mbedTLS: `sudo apt-get install -y build-essential pkg-config libmbedtls-dev`
    - wolfSSL: `sudo apt-get install -y build-essential pkg-config libwolfssl-dev`
  - macOS (Homebrew): `brew install openssl@3`
    - If not auto-detected: `export CPPFLAGS=$(brew --prefix openssl@3)/include` and `export LDFLAGS="-L$(brew --prefix openssl@3)/lib"`
- Build:
```bash
# Default: OpenSSL backend
make

# Choose TLS backend
make TLS_BACKEND=mbedtls
make TLS_BACKEND=wolfssl

# Print deps guidance for your OS
make deps
```

ภาษาไทย
- Makefile จะดาวน์โหลด Mongoose ไปไว้ที่ `../common-c/` ให้อัตโนมัติเมื่อ build ครั้งแรก
- รองรับ TLS backend: OpenSSL (ค่าเริ่มต้น), mbedTLS, wolfSSL กำหนดด้วย `TLS_BACKEND=...`
- ติดตั้งแพ็กเกจตามระบบปฏิบัติการ:
  - Debian/Ubuntu (รวมถึง Raspberry Pi):
    - OpenSSL: `sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev`
    - mbedTLS: `sudo apt-get install -y build-essential pkg-config libmbedtls-dev`
    - wolfSSL: `sudo apt-get install -y build-essential pkg-config libwolfssl-dev`
  - macOS (Homebrew): `brew install openssl@3` และตั้งค่า `CPPFLAGS/LDFLAGS` หากระบบหาไม่เจออัตโนมัติ
- คำสั่ง build และตรวจสอบ dependencies: ดูตัวอย่างด้านบน (make, make TLS_BACKEND=..., make deps)

Install prerequisites

- Linux (Ubuntu/Debian):
  - OpenSSL: `sudo apt-get install -y build-essential libssl-dev`
  - mbedTLS: `sudo apt-get install -y libmbedtls-dev`
  - wolfSSL: `sudo apt-get install -y libwolfssl-dev`
- macOS (Homebrew):
  - OpenSSL: `brew install openssl@3`
  - Optionally export `CPPFLAGS`/`LDFLAGS` if not auto-detected.
- Raspberry Pi OS: same as Ubuntu/Debian instructions.
- RTOS: use this code as reference; integrate per RTOS Mongoose porting guide.

Run — HTTPS (mTLS)

```bash
COMM_MODE=HTTPS \
API_BASE_URL=https://localhost:9444 \
CERTS_DIR=./certs_credentials \
./device_client
```

Run — MQTTS (mTLS)

```bash
COMM_MODE=MQTTS \
MQTT_HOST=localhost MQTT_PORT=8883 \
CERTS_DIR=./certs_credentials \
./device_client
```

Behavior

- Builds JSON `{device_id, timestamp, data}` โดยอ่านโครงสร้างฟิลด์จากไฟล์ schema หากมี
  - ค้นหาอัตโนมัติที่ `../download/data_schema.txt` (หรือกำหนดด้วย `SCHEMA_PATH`)
  - รองรับชนิด `integer/number/string/boolean` พร้อม minimum/maximum และ `enum` (เลือกค่าตัวแรก)
  - หากไม่พบไฟล์ schema จะ fallback เป็นฟิลด์ตัวอย่างเดิม
- TLS verification is enforced. Do not disable SSL. Paths are read from `CERTS_DIR/`.
- Reads `endpoints.json` if present and uses `api_base_url` or `ingest_base_url`.
- Device ID is read from `device_id.txt` or overridden by `DEVICE_ID` env var.

องค์ความรู้ (Knowledge)
- โครงสร้าง payload แบบ schema‑driven: โปรแกรมอ่านสคีมาจาก `../download/data_schema.txt` (หรือ `SCHEMA_PATH`) แล้วสร้างค่าแบบสุ่มที่สอดคล้องกับข้อกำหนดของแต่ละฟิลด์ (range/enum/type) เพื่อให้การทดสอบสะท้อนรูปแบบข้อมูลจริง
- การจับคู่พอร์ต: mTLS → HTTPS ใช้ 9444, MQTTS ใช้ 8883 ตามการออกแบบของแพลตฟอร์ม เพื่อลดโอกาสผิดพลาดเรื่อง SAN/ALPN และนโยบายความปลอดภัย
- Trust model: การยืนยันฝั่ง TLS ใช้ system trust ของเครื่องเพื่อเชื่อถือ `tesaiot.com` ไม่ควรวาง CA ผิดโดเมนทับซ้อน (หลีกเลี่ยง CA ที่ไม่เกี่ยวข้อง)
- CSR device: ตามหลักการความปลอดภัย bundle ที่สร้างจาก CSR จะไม่มี private key ใน ZIP จำเป็นต้องวางกุญแจที่ผลิตจากฝั่งอุปกรณ์ลง `certs_credentials/client_key.pem` ก่อนใช้งาน

Troubleshooting (ข้อผิดพลาดพบบ่อย)
- TLS Handshake สำเร็จแต่ส่งไม่ผ่าน (HTTPS 4xx): ตรวจ `X-API-KEY` สำหรับโหมด serverTLS (mTLS ไม่ใช้ API key), ตรวจเวลาระบบ/รูปแบบ timestamp ตามสคีมา
- mTLS ขึ้น error ว่าไม่มี private key: รัน `./scripts/sync_csr_key.sh <DEVICE_ID>` เพื่อคัดลอกจาก `./csr/`
- SAN/โดเมนไม่ตรง: ตรวจว่าคุณใช้ `https://localhost:9444` สำหรับ ingest mTLS (ไม่ใช้พอร์ต 443)
- ข้อมูลไม่ตรงสคีมา: กำหนด `SCHEMA_PATH=/path/to/data_schema.txt` เพื่อชี้ไฟล์สคีมาที่ต้องการ

Advanced Topics (EN/TH)
- EN: Environment variables
  - `COMM_MODE` (HTTPS|MQTTS), `API_BASE_URL`, `MQTT_HOST`, `MQTT_PORT`, `CERTS_DIR`, `SCHEMA_PATH`, `TLS_BACKEND`
  - Tuning: `--period` (minutes), `--interval` (seconds)
- TH: ตัวแปรสำคัญ
  - `COMM_MODE`, `API_BASE_URL`, `MQTT_HOST`, `MQTT_PORT`, `CERTS_DIR`, `SCHEMA_PATH`, `TLS_BACKEND`
  - ปรับความถี่ส่งด้วย `--period` และ `--interval`

- EN: Cross‑platform notes
  - Linux / Raspberry Pi: install dev packages (see Build section). ARM/aarch64 works out‑of‑the‑box
  - macOS: Homebrew OpenSSL is auto‑detected; export CPPFLAGS/LDFLAGS if needed
- TH: หมายเหตุการใช้งานข้ามแพลตฟอร์ม
  - Linux / Raspberry Pi: ติดตั้งแพ็กเกจพัฒนาให้ครบ (ดู Build)
  - macOS: ใช้ Homebrew OpenSSL และตั้งค่า CPPFLAGS/LDFLAGS หากระบบหาไม่เจออัตโนมัติ

Legacy Clients (optional)

- See `./c/` for simple libmosquitto/libcurl senders (kept for comparison). The default build uses Mongoose.
CLI Flags

- `--mode HTTPS|MQTTS`: force transport, overrides `COMM_MODE` env.
- `--host <host>` and `--port <n>`: override MQTT host/port (MQTTS) or base host/port (HTTPS when combined with `API_BASE_URL`).
- `--period <minutes>`: total send duration in minutes.
- `--interval <seconds>`: send interval in seconds.

Test Results (2025‑09‑15) — 2‑minute run

- HTTPS mTLS: OK. Published telemetry every 10s for 2 minutes.
  - Command:
    - `COMM_MODE=HTTPS API_BASE_URL=https://localhost:9444 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - Notes: client cert/key were used; server TLS verification via system trust (public CA) succeeded.
- MQTTS mTLS (port 8883): OK. Published every 10s for 2 minutes.
  - Command:
    - `COMM_MODE=MQTTS CERTS_DIR=./certs_credentials ./device_client --host localhost --port 8883 --period 2 --interval 10`
  - Notes: TLS handshake and PUBACK received (QoS1) each cycle.

Recommendations

- For HTTPS mTLS: no further action needed; current config works with system trust for tesaiot.com.
- For MQTTS mTLS: verify that the device’s client certificate is authorized on the broker and that the broker maps client cert to permissions for topic `device/<device_id>/telemetry`.

Schema Tips
- ไฟล์ schema ใช้ตามตัวอย่าง `download/data_schema.txt` (JSON Schema แบบเรียบง่าย)
- หากเป็น CSR device ให้ซิงค์ private key ไปที่ `certs_credentials/client_key.pem` ก่อนใช้งาน mTLS
  - สคริปต์ช่วย: `./scripts/sync_csr_key.sh <DEVICE_ID>`
