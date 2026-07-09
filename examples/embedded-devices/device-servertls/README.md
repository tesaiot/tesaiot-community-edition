# TESA IoT Device → Platform (Server-TLS) — HTTPS or MQTTS via Mongoose

Unified, beginner-friendly C example that can send telemetry over either:
- **HTTPS Server-TLS** (API key + CA)
- **MQTTS Server-TLS** (username/password + CA)

Uses Cesanta Mongoose single-file library with TLS backends: OpenSSL, mbedTLS, or wolfSSL.

## Prerequisites

| Item | Description |
|------|-------------|
| GCC/Clang | C compiler with C11 support |
| OpenSSL/mbedTLS/wolfSSL | TLS library |
| Credentials | Server-TLS bundle from TESAIoT Platform |

## Getting Credentials from TESAIoT Platform

### Step 1: Download Server-TLS Bundle

1. Login to **TESAIoT Admin Portal**: https://admin.tesaiot.com
2. Navigate to **Devices** > Select your device
3. Go to the **Credentials** tab
4. Click **Download Server-TLS Bundle** (MQTT or HTTPS)
   - For MQTT: Enable `include_password` option
   - For HTTPS: Enable `include_api_key` option
5. Extract the bundle to get:
   - `ca-chain.pem` - CA certificate chain
   - `endpoints.json` - Connection endpoints
   - `mqtt-credentials.txt` or `https-api-credentials.txt` - Credentials

### Step 2: Sync Credentials

```bash
# Sync credentials to certs_credentials folder
make prepare
# Or manually:
./scripts/sync_credentials.sh --device-dir ../download
```

### Step 3: Shared Credentials (Alternative)

Store in shared credentials folder:
```bash
cp -r /path/to/downloaded/bundle/* ../../shared/devices_credentials/<device-name>/
```

> **Note**: The `examples/shared/devices_credentials/` folder is for storing downloaded credentials. This folder is NOT committed to git repositories.

---

## Quick Start (EN)
- Download Server‑TLS bundles in Admin UI → Credentials (include_password / include_api_key if needed)
- `make prepare` to sync into `./certs_credentials`
- Run for 2 minutes (every 10s):
  - HTTPS: `COMM_MODE=HTTPS API_BASE_URL=https://localhost CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`
  - MQTTS: `COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8884 CERTS_DIR=./certs_credentials ./device_client --period 2 --interval 10`

สรุปเริ่มต้นเร็ว (TH)
- ดาวน์โหลด Server‑TLS bundles จาก Admin UI (เลือก include_password/include_api_key เมื่อจำเป็น)
- รัน `make prepare` เพื่อซิงค์ให้ตรงกับฐานข้อมูล
- รันทดสอบ 2 นาที (ส่งทุก 10 วินาที): HTTPS และ MQTTS ตามคำสั่งด้านบน

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

- Get Device02 Server‑TLS bundle from Admin UI → Credentials → “Download Server‑TLS bundle”.
- Then:

```bash
make prepare
```

Build / ติดตั้งไลบรารี

English
- The Makefile auto-fetches Mongoose into `../common-c/` on first build.
- TLS backends supported: OpenSSL (default), mbedTLS, wolfSSL. Pick via `TLS_BACKEND=...`.
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

Run — HTTPS (Server‑TLS)

```bash
COMM_MODE=HTTPS \
API_BASE_URL=https://localhost \
CERTS_DIR=./certs_credentials \
./device_client
```

Run — MQTTS (Server‑TLS)

```bash
COMM_MODE=MQTTS \
MQTT_HOST=localhost MQTT_PORT=8884 \
CERTS_DIR=./certs_credentials \
./device_client
```

Behavior

- Builds JSON `{device_id, timestamp, data}` โดยอ่านโครงสร้างฟิลด์จากไฟล์ schema หากมี
  - ค้นหาอัตโนมัติที่ `../download/data_schema.txt` (หรือกำหนดด้วย `SCHEMA_PATH`)
  - รองรับชนิด `integer/number/string/boolean` พร้อม minimum/maximum และ `enum` (เลือกค่าตัวแรก)
  - หากไม่พบไฟล์ schema จะ fallback เป็นฟิลด์ตัวอย่างเดิม
- HTTPS ใช้เฉพาะ `X-API-KEY: <api_key.txt>` (ไม่ต้องส่ง Bearer)
- TLS verification is enforced. Do not disable SSL. Paths are read from `CERTS_DIR/`.
- Reads `endpoints.json` if present and uses `api_base_url` or `ingest_base_url`; also reads `mqtt_host` and `mqtt_tls_port` if present.
- Device ID is read from `device_id.txt` or overridden by `DEVICE_ID` env var.

องค์ความรู้ (Knowledge)
- โครงสร้าง payload แบบ schema‑driven: โปรแกรมอ่านสคีมาจาก `../download/data_schema.txt` (หรือ `SCHEMA_PATH`) และสุ่มค่าให้สอดคล้องกับ type/min-max/enum ช่วยให้ทดสอบกับข้อมูลจริงได้รวดเร็ว
- การเลือกพอร์ต: serverTLS (user/pass) → MQTT ใช้ 8884, HTTPS ใช้ 443; mTLS แยกไป 8883/9444 ตามนโยบาย แยกเส้นทางชัดเจนลดความสับสน
- การยืนยันสิทธิ์: HTTPS ใช้เฉพาะ `X-API-KEY`, MQTTS ใช้ `username=device_id` และ `password` จาก bundle ที่ include_password=true เท่านั้น และ backend จะตรวจ hash ในฐานข้อมูล
- ACL โทปิค: อนุญาตเฉพาะ `device/<device_id>/telemetry` สำหรับ publish (subscribe ใช้ `device/<device_id>/commands|config|firmware`)

Troubleshooting (ข้อผิดพลาดพบบ่อย)
- HTTPS 401: API key ไม่อัปเดต → ดาวน์โหลด HTTPS bundle ใหม่แบบ include_api_key=true แล้วรัน `./scripts/sync_credentials.sh --device-dir ../download`
- MQTTS Code 5 (Not authorized): username ไม่ตรงกับ device_id หรือ password หมดอายุ/ยังไม่ได้รีเซ็ต → ดาวน์โหลด MQTT Server‑TLS bundle แบบ include_password=true แล้วซิงค์ใหม่
- พอร์ตสลับกับ mTLS: ถ้าไป 8883 จะเจอ TLS ปิด connection หลัง CONNECT เพราะโหมดไม่ตรง → ใช้ 8884 สำหรับ serverTLS
- ACL deny: ตรวจว่า topic เป็น `device/<device_id>/telemetry` และ client_id ตรงกับ `<device_id>`

Legacy Clients (optional)

- See `./c/` for simple libmosquitto/libcurl senders (kept for comparison). The default build uses Mongoose.
Test Results (2025‑09‑15) — 2‑minute run

- HTTPS Server‑TLS: OK. ส่งสำเร็จทุก 10 วินาทีในช่วง 2 นาที (ต้องแน่ใจว่า `api_key.txt` เป็นชุดล่าสุดจาก HTTPS bundle)
- MQTTS Server‑TLS (port 8884): OK. ส่งสำเร็จทุก 10 วินาทีในช่วง 2 นาที (หลังซิงค์รหัสผ่านใหม่จาก bundle)

Notes

- To enable MQTTS in Server‑TLS mode, ensure `mqtt_username.txt` and `mqtt_password.txt` are valid for this device, and that ACL permits publishing to `device/<device_id>/telemetry` on port 8884.
- TLS verification remained enabled at all times; no SSL weakening.

Schema Tips
- วาง `download/data_schema.txt` ไว้ที่โฟลเดอร์ตัวอย่าง หรือกำหนด `SCHEMA_PATH` ให้โปรแกรมอ่าน
- หาก HTTPS 401 ให้กดดาวน์โหลด HTTPS Server‑TLS bundle ใหม่โดยเลือก include_api_key=true แล้วรันสคริปต์ซิงค์อีกครั้ง:
  - `./scripts/sync_credentials.sh --device-dir ../download`
