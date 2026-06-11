# ความปลอดภัย: serverTLS และ mTLS

TESAIoT Community Edition รองรับการยืนยันตัวตน 2 โหมด สำหรับทั้ง HTTP gateway และ MQTT broker:

- **serverTLS** — เข้ารหัสการเชื่อมต่อ และไคลเอนต์ตรวจสอบใบรับรองของเซิร์ฟเวอร์ (ฝั่งเดียว)
- **mTLS (mutual TLS)** — ทั้งสองฝั่งตรวจสอบใบรับรองกัน อุปกรณ์ต้องนำเสนอใบรับรองไคลเอนต์ที่
  ออกโดย Vault PKI

## ใบรับรองมาจากไหน

| ขั้น | แหล่งใบรับรอง |
|---|---|
| boot ครั้งแรก | `generate-secrets.sh` เขียน CA + server cert แบบ self-signed ลง `./config/tls` |
| หลัง init PKI | `init-vault-pki.sh` + vault-agent แทนที่ด้วยใบรับรองที่ออกจาก Vault PKI (pki-int) |

ไฟล์ภายใต้ `./config/tls`:

```
server-cert.pem   ใบรับรองเซิร์ฟเวอร์
server-key.pem    private key (ห้าม commit)
ca-bundle.pem     CA bundle ใช้ตรวจสอบใบรับรองไคลเอนต์ (mTLS)
```

## serverTLS

เป็นโหมดเริ่มต้นและพร้อมใช้ทันทีหลัง `make install`

### nginx (HTTP)

nginx terminate TLS ที่พอร์ต 443 และ 9444 (ingest) ใช้ `server-cert.pem` + `server-key.pem`
จาก `./config/tls` (mount ไปที่ `/etc/nginx/certs`)

### APISIX (gateway)

APISIX โหมด standalone YAML เก็บใบรับรองเซิร์ฟเวอร์ไว้ในบล็อก `ssls` ของ
`config/apisix/apisix.yaml`:

```yaml
ssls:
  - id: 1
    snis:
      - "localhost"
      - "tesa.iot"
    cert: |
      -----BEGIN CERTIFICATE-----
      ...ใบรับรองที่ออกจาก Vault PKI...
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      ...private key...
      -----END PRIVATE KEY-----
```

> แทนที่ค่า placeholder `CHANGEME_REPLACE_WITH_VAULT_PKI_...` ด้วยใบรับรองจริงจาก Vault PKI
> **ห้าม commit private key จริง**

### EMQX (MQTT)

EMQX รับ serverTLS ที่พอร์ต **8884** vault-agent จะ render ใบรับรองเซิร์ฟเวอร์ลงใน volume
`emqx-certs` ตามค่า `EMQX_CERT_CN`, `EMQX_CERT_ALT_NAMES`, `EMQX_CERT_IP_SANS` ใน `.env`

ทดสอบ:

```bash
openssl s_client -connect localhost:8884 -servername localhost
```

## mTLS

โหมด mTLS บังคับให้อุปกรณ์นำเสนอใบรับรองไคลเอนต์ที่ออกจาก Vault PKI

### EMQX mTLS (พอร์ต 8883)

EMQX รับ mTLS ที่พอร์ต **8883** โดยตรวจสอบใบรับรองไคลเอนต์กับ CA bundle ของ Vault PKI
อุปกรณ์ต้องเชื่อมต่อพร้อม client cert + key:

```bash
mosquitto_pub \
  -h localhost -p 8883 \
  --cafile ca-bundle.pem \
  --cert device-cert.pem \
  --key device-key.pem \
  -t "devices/dev-001/telemetry" \
  -m '{"temp": 25.4}'
```

CN ในใบรับรองไคลเอนต์จะถูกใช้กำหนด identity ของอุปกรณ์ และ ACL จะตรวจผ่าน webhook ของ API

### APISIX mTLS

เปิด mTLS ที่ gateway โดยเพิ่มบล็อก `client` ในรายการ `ssls` พร้อม `ca` + `depth` และตั้ง
`verify_client: true` ดูตัวอย่างใน `config/apisix/mtls-routes.yaml`

หลังแก้ไขแล้ว restart:

```bash
docker compose restart apisix
```

### nginx mTLS

mTLS ingest บนพอร์ต `9444` **เปิดใช้งานเป็นค่าเริ่มต้น** ผ่าน
`config/nginx/conf.d/30-iot-mtls.conf` (render จาก `.tpl`) ด้วย `ssl_verify_client on;`
— fail closed: nginx จะยกเลิก TLS handshake ทันทีถ้าไคลเอนต์ไม่มีใบรับรองที่ chain ถึง
bundle ได้ ไฟล์ `ca-bundle.pem` เริ่มจาก bootstrap self-signed CA จากนั้น
`init-vault-pki.sh` จะ **append chain ของ Vault root + intermediate** เข้าไป — chain ที่ถูก
append นี่แหละที่ใช้ตรวจใบรับรองอุปกรณ์จริง การเปลี่ยนเป็น `optional` จะรองรับ fleet แบบผสม
(API ตัดสินรายคำขอ) แต่เสีย guarantee แบบ fail-closed — ไม่แนะนำ

## คำแนะนำสำหรับ production

- เปลี่ยนใบรับรอง self-signed ครั้งแรกเป็นใบรับรองจาก Vault PKI ทันที (รัน `make init-pki`)
- ใช้ mTLS (พอร์ต 8883) สำหรับอุปกรณ์ที่ต้องการความปลอดภัยสูง — ปิดพอร์ต plain MQTT 1883
- ปิดการเข้าถึงพอร์ตจัดการ (8200, 9180, 18083) จากอินเทอร์เน็ตด้วยไฟร์วอลล์
- ตั้ง TTL ใบรับรองสั้นและพึ่ง vault-agent ในการต่ออายุอัตโนมัติ (ดู [certificate-lifecycle.md](certificate-lifecycle.md))
- ตรวจสอบว่า private key ทั้งหมด (`server-key.pem`, device keys) ไม่เคยถูก commit เข้า git

## การ hardening TLS ที่ทำไว้แล้ว

- TLS 1.2 + 1.3 เท่านั้น; cipher list แบบ AEAD-only ที่ระบุชัด (ECDHE +
  AES-GCM/CHACHA20-POLY1305 — ไม่มี CBC, ไม่มี SHA-1) ทั้งบน nginx และ APISIX และตั้ง
  `ssl_session_tickets off`
- header: HSTS, `X-Frame-Options`, `X-Content-Type-Options` บน vhost serverTLS
- `server_tokens off`, มี rate-limit zone (`api_limit`, `auth_limit`)

## การเก็บรักษา unseal key ของ Vault

ในการติดตั้งแบบ single-host เริ่มต้น **unseal key ทั้ง 3 ส่วน (Shamir) และ root token
อยู่ใน `.env` บนเครื่องเดียวกับข้อมูลของ Vault** — และ vault-agent ใช้ 2 ส่วนในการ
self-unseal หลัง reboot (`VAULT_UNSEAL_KEYS` ใน `docker-compose.yml`) เป็น trade-off
ด้าน availability ที่จงใจสำหรับเครื่อง CE self-host: ใครอ่าน `.env` ได้ก็ unseal ได้อยู่แล้ว

สำหรับ production:

- **แยก key share** — ย้าย `VAULT_UNSEAL_KEY_2/3` ออกจาก `.env` ไปให้ผู้ถือแยกกัน
  (ปล่อย `VAULT_UNSEAL_KEYS` ว่างจะปิด self-unseal; การ unseal ต้องใช้ 2 ผู้ถือผ่าน
  `make unseal` หรือ `vault operator unseal`)
- **หรือใช้ cloud-KMS auto-unseal** — เปิดและตั้งค่า stanza `seal "awskms"` ใน
  `config/vault/vault-auto-unseal.hcl` แล้ว unseal material จะไม่แตะเครื่องเลย
- เก็บ **root token** ออกจากการใช้งานประจำวัน — แพลตฟอร์มใช้แค่ AppRole (vault-agent)
  และ token ที่ derive ออกมา
- **backup** ของ `.env` ที่เก็บนอกเครื่อง (ดู [backup-restore.md](backup-restore.md))
  เป็นส่วนหนึ่งของการดูแล key: ปฏิบัติกับ archive เหมือนกับตัว key

## ดูเพิ่มเติม

- [certificate-lifecycle.md](certificate-lifecycle.md) — การออก/ต่ออายุ/เพิกถอนใบรับรอง
- [mqtt-emqx.md](mqtt-emqx.md) — รายละเอียดโบรกเกอร์และพอร์ต
