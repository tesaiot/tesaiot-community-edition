# การสำรองและกู้คืนข้อมูล

TESAIoT Community Edition มีสคริปต์สำรอง/กู้คืนที่ครอบคลุมฐานข้อมูลและ secret/config ที่จำเป็นต่อการ
กู้คืน stack กลับมา

## สิ่งที่ถูกสำรอง

`scripts/backup.sh` จะ dump และเก็บ:

- **MongoDB** — ทะเบียนผู้ใช้/อุปกรณ์/ใบรับรอง
- **TimescaleDB** — ข้อมูล telemetry time-series
- **config/secrets** ที่จำเป็นต่อการกู้คืน: `.env`, mongo keyfile, TLS material, vault-agent approle
  รวมถึงไฟล์ config ที่ render แล้ว (emqx.conf, apisix.yaml ฯลฯ)
- **Vault storage** — snapshot ของ volume `vault-data` (ทั้ง PKI: กุญแจ CA, ทะเบียนใบรับรอง)
- **EMQX data** — snapshot ของ volume `emqx-data` (auth DB ภายใน, retained messages)

ผลลัพธ์: `./backups/tesaiot-community-edition-<timestamp>.tar.gz`

## การสำรอง

```bash
make backup
```

หรือเรียกสคริปต์ตรง:

```bash
./scripts/backup.sh
```

ไฟล์ backup จะถูกตั้งชื่อด้วย timestamp เช่น `backups/tesaiot-community-edition-20260608-143000.tar.gz`

> เก็บไฟล์ backup ไว้นอกเครื่อง (off-site) เพราะมี secret ทั้งหมดรวมถึง Vault unseal key
> และ root token

## การกู้คืน

stack ต้องทำงานอยู่ (อย่างน้อย mongodb + timescaledb) ก่อนกู้คืน:

```bash
make restore FILE=backups/tesaiot-community-edition-20260608-143000.tar.gz
```

หรือเรียกสคริปต์ตรง:

```bash
./scripts/restore.sh backups/tesaiot-community-edition-20260608-143000.tar.gz
```

`restore.sh` จะทำตามลำดับ:

1. แตกไฟล์ archive ไปยังไดเรกทอรีชั่วคราว
2. กู้คืน config + secret (`.env`, keyfile, TLS, approle)
3. โหลด dump ของ MongoDB กลับเข้าฐานข้อมูล
4. โหลด dump ของ TimescaleDB กลับเข้าฐานข้อมูล

## ขั้นตอนกู้คืนบนเครื่องใหม่ (disaster recovery)

**ต้อง restore ก่อน แล้วค่อย build/up** — การรัน `make up` บน clone เปล่า ๆ จะล้มเหลว
(ไม่มี `.env`, keyfile ถูกสร้างเป็นไดเรกทอรีโดย bind-mount, vault-agent ไม่มี AppRole):

```bash
# 1. clone โปรเจกต์และคัดลอกไฟล์ backup มาที่ ./backups
git clone <repo> && cd tesaiot-community-edition

# 2. กู้คืนรอบแรก: วาง .env / keyfile / TLS / approle / rendered configs
./scripts/restore.sh backups/tesaiot-community-edition-<timestamp>.tar.gz

# 3. build แล้วยก stack ขึ้น (ตอนนี้ compose มีทุกอย่างที่ต้องใช้แล้ว)
make build && make up

# 4. กู้คืนรอบสอง: โหลด dump ของฐานข้อมูล + volume vault-data/emqx-data
./scripts/restore.sh backups/tesaiot-community-edition-<timestamp>.tar.gz

# 5. unseal Vault (หรือปล่อยให้ vault-agent self-unseal จาก key ใน .env)
make unseal

# 6. ตรวจสุขภาพ
make restart && make health
```

## ข้อควรระวัง

- การกู้คืนจะ **เขียนทับ** ข้อมูลในฐานข้อมูลปัจจุบัน — ตรวจให้แน่ใจก่อนรัน
- `.env` ที่กู้คืนมาต้องตรงกับ secret เดิม (โดยเฉพาะ `JWT_SECRET`, Vault keys) มิฉะนั้น token/
  ใบรับรองเดิมจะใช้ไม่ได้
- ค่า `DEFAULT_ORG_ID` ต้องเหมือนกับตอน backup เสมอ

## การสำรองอัตโนมัติ (แนะนำ)

ตั้ง cron บน host เพื่อสำรองเป็นประจำ เช่น ทุกวันตี 2:

```cron
0 2 * * * cd /path/to/tesaiot-community-edition && make backup >> logs/backup.log 2>&1
```

หมุนเวียนลบไฟล์ backup เก่าเพื่อประหยัดพื้นที่

## ดูเพิ่มเติม

- [certificate-lifecycle.md](certificate-lifecycle.md) — Vault keys ที่ต้องสำรอง
- [upgrade.md](upgrade.md) — สำรองก่อนอัปเกรดเสมอ
