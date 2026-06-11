# การจัดการวงจรชีวิตใบรับรอง (Vault PKI)

TESAIoT Community Edition ใช้ HashiCorp Vault PKI เป็นศูนย์กลางในการ ออก (issue) ต่ออายุ (renew)
และ เพิกถอน (revoke) ใบรับรองสำหรับเซิร์ฟเวอร์และอุปกรณ์

## ลำดับชั้น PKI

`init-vault-pki.sh` สร้าง PKI 2 ชั้น:

```
pki-root   (Root CA)          ออกอายุยาว ใช้เซ็นเฉพาะ intermediate
   |
pki-int    (Intermediate CA)  ออกใบรับรองเซิร์ฟเวอร์/อุปกรณ์ทั้งหมด (mount = VAULT_PKI_PATH)
```

ค่า mount ของ issuing CA กำหนดผ่าน `VAULT_PKI_PATH` (ค่าเริ่มต้น `pki-int`)

## การ initialise

```bash
make init-pki
```

`init-vault-pki.sh` จะ:

1. รัน `vault operator init` (ถ้ายังไม่เคย) แล้วบันทึก unseal key + root token ลง `.env`
2. unseal Vault
3. สร้างลำดับชั้น PKI (pki-root → pki-int)
4. เขียน policy ของ API + role ของ device/service
5. เปิด AppRole ให้ Vault Agent ใช้
6. เปิด KV engine สำหรับเก็บใบรับรองอุปกรณ์

สคริปต์นี้ idempotent — รันซ้ำได้ จะตรวจจับ Vault ที่ init แล้วและ apply เฉพาะ policy/role ใหม่

## การต่ออายุอัตโนมัติ (vault-agent)

service `vault-agent` ทำหน้าที่ render และต่ออายุใบรับรองโดยอัตโนมัติ พฤติกรรมควบคุมด้วย
environment ใน `docker-compose.yml`:

```
NEXT_SECS:  604800    # ต่ออายุเมื่อเหลืออายุน้อยกว่า 7 วัน
SLEEP_SECS: 43200     # ตรวจสอบทุก 12 ชั่วโมง
```

ใบรับรองที่ vault-agent ดูแล:

- **ใบรับรองเซิร์ฟเวอร์ EMQX** — render ลง volume `emqx-certs` ตาม `EMQX_CERT_CN`,
  `EMQX_CERT_ALT_NAMES`, `EMQX_CERT_IP_SANS`
- **API token** — token ของ Vault ที่ API ใช้เรียก PKI (`/vault/token/api-token`)

> ค่า TTL และเกณฑ์ต่ออายุไม่ถูก hardcode — กำหนดผ่าน environment เสมอ

## การออกใบรับรองอุปกรณ์

API เรียก Vault PKI เพื่อออกใบรับรองอุปกรณ์ตอนลงทะเบียนอุปกรณ์ โดยใช้ token จากไฟล์
`VAULT_TOKEN_FILE` (`/vault/token/api-token`) และ role ที่กำหนดไว้ใน `init-vault-pki.sh`

ตัวจัดการใบรับรองในโค้ด API:

```
services/api/certificate_manager_vault.py
services/api/certificate_manager_vault_enhanced.py
services/api/vault_integration.py
services/api/vault_key_manager.py
```

ขั้นตอนทั่วไป (ผ่าน Admin UI หรือ API):

1. ลงทะเบียนอุปกรณ์ → API ขอ Vault ออกใบรับรองจาก `pki-int/issue/<role>`
2. ใบรับรอง + key + CA chain ถูกส่งกลับไปติดตั้งบนอุปกรณ์ (หรือฝังใน QR enroll)
3. metadata ของใบรับรอง (serial, อายุ, สถานะ) ถูกบันทึกใน MongoDB

## การเพิกถอน (revoke)

เมื่อเพิกถอนใบรับรองผ่าน Admin UI / API, API จะเรียก Vault ให้ revoke ตาม serial number
Vault จะเพิ่ม serial เข้าไปใน CRL (Certificate Revocation List) ของ pki-int อุปกรณ์ที่ถูก
เพิกถอนจะไม่ผ่านการตรวจสอบ mTLS อีกต่อไป

## การตรวจสอบ (monitoring)

API มี endpoint สำหรับติดตามสถานะใบรับรอง (ดู `services/api/api/routes_certificate_monitoring.py`)
ใช้ดูใบรับรองที่ใกล้หมดอายุและสถานะ revoke

## การปฏิบัติที่ดี

- ตั้ง TTL ใบรับรองให้สั้น (เช่น 30–90 วัน) และพึ่ง vault-agent ในการต่ออายุ
- สำรอง unseal key และ root token แยกที่ปลอดภัย (อยู่ใน `.env` — ดู [backup-restore.md](backup-restore.md))
- อย่าให้ Vault sealed ค้าง — หาก restart host ต้อง unseal ใหม่ (auto-unseal ตั้งค่าไว้แล้วใน config)
- ตรวจ CRL เป็นระยะเพื่อยืนยันว่าอุปกรณ์ที่ปลดระวางถูกเพิกถอนจริง

## ดูเพิ่มเติม

- [security-tls-mtls.md](security-tls-mtls.md) — การใช้ใบรับรองในโหมด TLS/mTLS
- [device-management.md](device-management.md) — การลงทะเบียนอุปกรณ์
