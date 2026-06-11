# การอัปเกรด

คู่มือนี้อธิบายการอัปเกรด TESAIoT Community Edition ไปยังเวอร์ชันใหม่อย่างปลอดภัย

## หลักการกำหนดเวอร์ชัน

โปรเจกต์ยึดตาม [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

```
MAJOR.MINOR.PATCH
```

- **MAJOR** — การเปลี่ยนแปลงที่ไม่เข้ากันย้อนหลัง (breaking change)
- **MINOR** — เพิ่มฟีเจอร์แบบเข้ากันย้อนหลังได้
- **PATCH** — แก้บั๊กแบบเข้ากันย้อนหลังได้

อ่านสิ่งที่เปลี่ยนในแต่ละเวอร์ชันได้ที่ [`CHANGELOG.md`](../../CHANGELOG.md) ซึ่งจัดรูปแบบตาม
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) เวอร์ชันปัจจุบันดูได้จาก `VERSION.txt`

## ก่อนอัปเกรด: สำรองข้อมูลเสมอ

```bash
make backup
```

เก็บไฟล์ backup ไว้นอกเครื่องก่อนดำเนินการต่อ (ดู [backup-restore.md](backup-restore.md))

## ขั้นตอนอัปเกรดมาตรฐาน

```bash
# 1. สำรองข้อมูล
make backup

# 2. ดึงโค้ดเวอร์ชันใหม่
git fetch --tags
git checkout v<เวอร์ชันใหม่>

# 3. ตรวจ CHANGELOG หา breaking change และตัวแปร .env ใหม่
#    เทียบ .env ของคุณกับ .env.example
diff <(grep -oE '^[A-Z_]+=' .env | sort -u) \
     <(grep -oE '^[A-Z_]+=' .env.example | sort -u)

# 4. build อิมเมจใหม่
make build

# 5. นำขึ้นใช้งาน (compose จะ recreate เฉพาะ container ที่เปลี่ยน)
make up

# 6. รันสคริปต์ init ที่เกี่ยวข้องซ้ำ (ทั้งหมด idempotent)
make init-pki
make init-db
make init-emqx
make init-apisix

# 7. ตรวจสุขภาพ
make health
```

## การจัดการตัวแปร .env ใหม่

เมื่ออัปเกรดอาจมีตัวแปรใหม่ใน `.env.example` ที่ `.env` ของคุณยังไม่มี ให้เพิ่มเข้าไปด้วยมือ
โดยอ้างค่าเริ่มต้นจาก `.env.example` **อย่าเขียนทับ `.env` เดิม** เพราะจะทำให้ secret และ Vault
key หายไป

## การจัดการไฟล์ config ที่ถูก render

ไฟล์ config ที่มี secret — `config/emqx/emqx.conf`, `config/apisix/config.yaml`,
`config/apisix/apisix.yaml`, `config/emqx/auth-built-in-db-bootstrap.csv` และ
`config/nginx/conf.d/30-iot-mtls.conf` — เป็นไฟล์ที่ถูก **generate ขึ้นมา** (และถูก
git-ignore): `generate-secrets.sh` จะ render แต่ละไฟล์จากเทมเพลต `<name>.tpl` ใหม่
ทุกครั้งที่รัน โดยฉีดค่า secret จาก `.env` **อย่าแก้ไฟล์ที่ถูก render โดยตรง — การแก้จะหาย
ตอน render รอบถัดไป** ถ้าต้องการปรับแต่ง ให้แก้ที่ไฟล์ `.tpl` แล้วรัน
`./scripts/generate-secrets.sh` ใหม่ (idempotent) หลังดึง release ใหม่ ให้ตรวจการ
เปลี่ยนแปลงของไฟล์ `*.tpl` แล้ว render ใหม่

## การอัปเกรดเวอร์ชันอิมเมจของ infra

เวอร์ชันอิมเมจ (vault, mongo, timescaledb, redis, emqx, apisix, nginx) ถูกตรึงใน
`docker-compose.yml` หากต้องเปลี่ยน:

1. แก้ tag ใน `docker-compose.yml`
2. อ่าน release note ของอิมเมจนั้น โดยเฉพาะ MongoDB และ TimescaleDB ที่อาจต้องทำ migration
3. สำรองข้อมูลก่อน แล้ว `make up`

> ข้ามเวอร์ชัน major ของฐานข้อมูลหลายขั้นพร้อมกันไม่แนะนำ — อัปเกรดทีละขั้น

## การ rollback

หากอัปเกรดแล้วมีปัญหา:

```bash
# 1. กลับไปเวอร์ชันโค้ดเดิม
git checkout v<เวอร์ชันเดิม>

# 2. build + up
make build
make up

# 3. ถ้าข้อมูลเสียหาย ให้กู้คืนจาก backup ก่อนอัปเกรด
make restore FILE=backups/tesaiot-community-edition-<timestamp>.tar.gz
```

## ตรวจสอบหลังอัปเกรด

```bash
make health
make logs s=api          # ดูว่า API เริ่มได้โดยไม่มี error
cat VERSION.txt          # ยืนยันเวอร์ชัน
```

ทดสอบฟังก์ชันหลัก: login Admin UI, ดูรายการอุปกรณ์, ตรวจว่า telemetry ยังเข้าฐานข้อมูล

## ดูเพิ่มเติม

- [backup-restore.md](backup-restore.md)
- [troubleshooting.md](troubleshooting.md)
- [`CHANGELOG.md`](../../CHANGELOG.md)
