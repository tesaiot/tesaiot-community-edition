# การตั้งค่า

การตั้งค่าทั้งหมดของ TESAIoT Community Edition ทำผ่านไฟล์ `.env` ที่ root ของโปรเจกต์ ตามหลัก
Twelve-Factor (config-in-environment) จะไม่มีการ hardcode ค่าใด ๆ ลงในโค้ดหรือ
`docker-compose.yml` — ทุก secret อ่านจาก `.env`

## สร้างไฟล์ `.env`

```bash
cp .env.example .env
```

หรือใช้สคริปต์สร้าง secret แบบสุ่มอัตโนมัติ:

```bash
./scripts/generate-secrets.sh
# หรือพร้อมระบุโดเมน
./scripts/generate-secrets.sh --domain=example.com
# เขียนทับไฟล์เดิม
./scripts/generate-secrets.sh --force
```

> **อย่า commit ไฟล์ `.env`** เพราะมี secret จริง ทุกค่าที่ขึ้นต้นด้วย `CHANGEME_` ต้องถูกแทนที่
> ก่อน boot ครั้งแรก

## หมวดการตั้งค่า

### อัตลักษณ์การ deploy

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `DOMAIN` | `localhost` | โดเมน/host สาธารณะ ใช้สร้าง TLS SAN และ public URL |
| `DEFAULT_ORG_ID` | `default-org` | id ขององค์กรเดียว — **ห้ามเปลี่ยนหลัง boot ครั้งแรก** เพราะถูกเขียนลงข้อมูล |
| `TZ` | `Asia/Bangkok` | โซนเวลา |
| `BUILD_TAG` | `latest` | tag ของอิมเมจ |

### HashiCorp Vault (PKI + secrets)

| ตัวแปร | หมายเหตุ |
|---|---|
| `VAULT_UNSEAL_KEY_1..3` | เว้นว่างสำหรับติดตั้งใหม่ — สคริปต์ init จะเติมให้หลัง `vault operator init` |
| `VAULT_ROOT_TOKEN` | root token ของ Vault (เก็บเป็นความลับ) |
| `VAULT_PKI_PATH` | mount path ของ intermediate PKI engine (ค่าเริ่มต้น `pki-int`) |

### MongoDB

| ตัวแปร | ค่าเริ่มต้น |
|---|---|
| `MONGO_INITDB_ROOT_USERNAME` | `mongoadmin` |
| `MONGO_INITDB_ROOT_PASSWORD` | `CHANGEME_...` |
| `MONGO_INITDB_DATABASE` | `tesa_iot` |
| `MONGODB_USER` | `iot_user` (user ที่ API ใช้เชื่อมต่อ) |
| `MONGODB_PASSWORD` | `CHANGEME_...` |
| `MONGODB_DATABASE` | `tesa_iot` |
| `MONGODB_AUTH_SOURCE` | `admin` |

### TimescaleDB / PostgreSQL

| ตัวแปร | ค่าเริ่มต้น |
|---|---|
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | `CHANGEME_...` |
| `POSTGRES_DB` | `tesa_telemetry` |

### Redis

| ตัวแปร | หมายเหตุ |
|---|---|
| `REDIS_PASSWORD` | รหัสผ่าน Redis (cache + rate-limit) |

### API service (auth / JWT / bootstrap admin)

| ตัวแปร | ค่าเริ่มต้น | หมายเหตุ |
|---|---|---|
| `JWT_SECRET` | `CHANGEME_...` | secret เซ็น JWT (HS256) ต้องยาวและสุ่ม |
| `SECRET_KEY` | `CHANGEME_...` | Flask secret key |
| `BCRYPT_LOG_ROUNDS` | `12` | cost factor ของ bcrypt (อ่านจาก env เสมอ ไม่ hardcode) |
| `ADMIN_EMAIL` | `admin@localhost` | admin เริ่มต้น |
| `ADMIN_USERNAME` | `admin` | |
| `ADMIN_PASSWORD` | `CHANGEME_...` | |
| `ADMIN_BYPASS_RATE_LIMIT` | `true` | ให้ admin ข้าม rate limit การ login ต่อ IP |
| `LOG_LEVEL` | `INFO` | |

#### Public URL ที่ประกาศให้อุปกรณ์

```
TESA_PUBLIC_API_BASE_URL=https://localhost
TESA_PUBLIC_INGEST_BASE_URL=https://localhost:9444
TESA_PUBLIC_MQTT_HOST=localhost
TESA_PUBLIC_MQTT_TLS_PORT=8884
TESA_PUBLIC_MQTT_MTLS_PORT=8883
TESA_PUBLIC_MQTT_WS_PORT=8083
```

### Email / OTP (ไม่บังคับ)

ตั้ง `EMAIL_ENABLED=false` เพื่อให้ระบบ log อีเมลออก stdout แทนการส่งจริง (เหมาะกับ dev)

| ตัวแปร | ค่าเริ่มต้น |
|---|---|
| `EMAIL_ENABLED` | `false` |
| `EMAIL_HOST` | `smtp.example.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `true` |
| `EMAIL_FROM_ADDRESS` | `noreply@localhost` |
| `EMAIL_PROVIDER` | `smtp` (รองรับ `resend` ผ่าน `RESEND_API_KEY`) |
| `OTP_LENGTH` | `6` |
| `OTP_EXPIRE_MINUTES` | `15` |
| `OTP_MAX_ATTEMPTS` | `3` |
| `OTP_COOLDOWN_SECONDS` | `30` |

### EMQX MQTT broker

| ตัวแปร | หมายเหตุ |
|---|---|
| `EMQX_DASHBOARD_PASSWORD` | รหัสผ่าน dashboard (`http://localhost:18083`) |
| `EMQX_WEBHOOK_SECRET` | bearer secret ที่ EMQX ส่งให้ webhook auth/ACL ของ API |
| `EMQX_CERT_CN` | CN ของใบรับรองเซิร์ฟเวอร์ EMQX (ค่าเริ่มต้นตาม `DOMAIN`) |
| `EMQX_CERT_ALT_NAMES` | SAN เพิ่มเติม เช่น `localhost,mqtt.localhost` |
| `EMQX_CERT_IP_SANS` | IP SAN เช่น `127.0.0.1` |

### ข้อมูลรับรอง MQTT

| ตัวแปร | หมายเหตุ |
|---|---|
| `MQTT_USERNAME` | `mqtt_user` |
| `MQTT_PASSWORD` | `CHANGEME_...` |
| `MQTT_BRIDGE_PASSWORD` | รหัสผ่านของ user ที่ telemetry bridge ใช้เชื่อม EMQX |
| `BRIDGE_API_USER` | บัญชี API ที่ bridge ใช้ login เพื่อ forward telemetry (ต้องมีอยู่ในทะเบียนผู้ใช้) |
| `BRIDGE_API_PASSWORD` | รหัสผ่านของบัญชีข้างต้น |

### APISIX API gateway

| ตัวแปร | หมายเหตุ |
|---|---|
| `APISIX_ADMIN_KEY` | admin API key (32+ ตัวอักษร) |
| `APISIX_ADMIN_URL` | `http://tesa-apisix:9180/apisix/admin` |

### TLS

| ตัวแปร | หมายเหตุ |
|---|---|
| (ไม่มีตัวแปร) | ไดเรกทอรี TLS ถูกกำหนดตายตัวที่ `./config/tls` ใน docker-compose.yml (ไม่มี env override) |

ไฟล์ที่คาดหวังภายใต้ `./config/tls`: `server-cert.pem`, `server-key.pem`, `ca-bundle.pem`
โดย `generate-secrets.sh` เขียน CA + server cert แบบ self-signed ครั้งแรก แล้ว
`init-vault-pki.sh` / vault-agent จะแทนที่ด้วยใบรับรองที่ออกโดย Vault PKI

## การนำค่ามาใช้

หลังแก้ไข `.env` ให้ restart service ที่เกี่ยวข้อง:

```bash
make restart            # restart ทั้งหมด
make restart s=api      # restart เฉพาะ service เดียว
```

บาง service (เช่น APISIX admin key) ต้องรันสคริปต์ init ซ้ำ:

```bash
make init-apisix
docker compose restart apisix
```

## หลักการสำคัญ

- ห้าม hardcode ค่า — ใช้ `.env` หรือ override ผ่าน environment เสมอ
- ค่า TTL, validity_days, provisioning_method ต้องคำนวณจากข้อมูลจริงหรือกำหนดผ่าน config
- ห้ามใช้ `docker compose` ตรง ๆ ในการ deploy — ใช้ make target / สคริปต์เสมอ
