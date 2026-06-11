# การแก้ปัญหา

คู่มือนี้รวบรวมปัญหาที่พบบ่อยและวิธีวินิจฉัย TESAIoT Community Edition

## เครื่องมือวินิจฉัยพื้นฐาน

```bash
make ps                 # สถานะ container
make health             # ตรวจสุขภาพทุก service พร้อมตาราง UP/WARN/DOWN
make logs               # ดู log ทั้งหมด
make logs s=api         # ดู log เฉพาะ service เดียว
docker compose ps       # รายละเอียดเพิ่มเติม
```

## ปัญหาตอนติดตั้ง

### preflight ล้มเหลว

```bash
make preflight
```

ตรวจประเด็นที่สคริปต์รายงาน:

- **Docker ไม่ติดตั้ง** — ติดตั้งจาก https://docs.docker.com/engine/install/
- **ไม่มี Docker Compose v2** — ต้องเป็นปลั๊กอิน `docker compose` ไม่ใช่ `docker-compose` เก่า
- **พอร์ตชนกัน** — มีบริการอื่นใช้พอร์ต 80/443/1883/8200 ฯลฯ อยู่ ให้หยุดหรือเปลี่ยนพอร์ต
  (API พอร์ต 5566 และ MongoDB 27017 ไม่ถูก publish บน host)
- **ดิสก์ไม่พอ** — ต้องมีพื้นที่ว่างอย่างน้อย 20 GB
- **ไม่มี openssl** — ติดตั้งก่อนรัน `generate-secrets.sh`

### ยังมีค่า CHANGEME_ ใน .env

ทุกค่าที่ขึ้นต้นด้วย `CHANGEME_` ต้องถูกแทนที่ก่อน boot รัน:

```bash
./scripts/generate-secrets.sh
```

## Vault sealed / API ติดต่อ Vault ไม่ได้

อาการ: API log แสดงข้อผิดพลาดเรื่อง Vault หรือ token

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 tesa-vault vault status
```

ถ้า sealed = true:

- **ปกติจะหายเองภายใน ~30 วินาที** — side-car vault-agent เฝ้าดู seal status และ
  unseal อัตโนมัติด้วย key share `VAULT_UNSEAL_KEY_*` จาก `.env`
  (ส่งผ่านเป็น `VAULT_UNSEAL_KEYS` ใน docker-compose.yml; เว้นว่างเพื่อปิดความสามารถนี้)
- **กู้คืนด้วยมือ** (ถ้าปิด self-unseal ไว้ หรือ vault-agent ล่มเอง):

```bash
make unseal          # ./scripts/unseal-vault.sh (idempotent)
```

- ถ้า key ใน `.env` ว่าง แปลว่า Vault ยังไม่เคยถูก initialise — รัน:

```bash
make init-pki        # initialise/unseal และ apply policy/role ซ้ำ (idempotent)
```

ตรวจว่า vault-agent สร้าง API token แล้ว:

```bash
docker exec tesa-vault-agent cat /vault/token/api-token
```

## API ไม่ healthy

```bash
make logs s=api
# API ไม่ถูก publish บน host (เข้าผ่าน nginx หรือ probe ในคอนเทนเนอร์)
curl -k https://localhost/api/v1/health
docker exec tesa-api curl -fsS http://localhost:5566/api/v1/health
```

สาเหตุที่พบบ่อย:

- MongoDB / TimescaleDB / Redis ยังไม่พร้อม — ตรวจ `make health` ของฐานข้อมูล
- secret ไม่ถูกต้อง (`JWT_SECRET`, `MONGODB_PASSWORD`, ฯลฯ)
- Vault token ยังไม่ถูก render โดย vault-agent

## MongoDB replica set ไม่ทำงาน

MongoDB รันเป็น single-node replica set (`rs0`) ถ้า init ไม่สำเร็จ:

```bash
make init-db
docker exec -it tesa-mongodb mongosh --eval "rs.status()"
```

## ปัญหา MQTT / EMQX

### อุปกรณ์เชื่อมต่อไม่ได้

```bash
make logs s=emqx
docker exec tesa-emqx emqx ctl status
docker exec tesa-emqx emqx ctl listeners
```

ตรวจ:

- ใช้พอร์ตถูกโหมด (1883 plain, 8883 mTLS, 8884 serverTLS)
- webhook auth ของ API ตอบ 200 — ตรวจ `EMQX_WEBHOOK_SECRET` ตรงกันทั้งสองฝั่ง
- สำหรับ mTLS: ใบรับรองไคลเอนต์ออกจาก Vault PKI เดียวกันและยังไม่ถูกเพิกถอน

### telemetry ไม่เข้าฐานข้อมูล

```bash
make logs s=mqtt-bridge
```

ตรวจว่า `BRIDGE_API_USER` มีอยู่ในทะเบียนผู้ใช้และ `BRIDGE_API_PASSWORD` ถูกต้อง

## ปัญหา TLS / ใบรับรอง

### เบราว์เซอร์เตือนใบรับรองไม่น่าเชื่อถือ

ครั้งแรกใช้ใบรับรอง self-signed ซึ่งจะถูกแทนที่ด้วยใบรับรองจาก Vault PKI หลัง `make init-pki`
สำหรับ production ให้ติดตั้ง CA ของ Vault PKI ในเครื่องไคลเอนต์ หรือใช้ใบรับรองจาก CA สาธารณะ

### APISIX serverTLS ไม่ทำงาน

ตรวจว่าได้แทนที่ placeholder `CHANGEME_REPLACE_WITH_VAULT_PKI_...` ในบล็อก `ssls` ของ
`config/apisix/apisix.yaml` แล้ว restart:

```bash
docker compose restart apisix
```

## ปัญหา APISIX gateway

```bash
make logs s=apisix
curl -i http://localhost:9080/
```

ถ้า admin key ยังเป็น placeholder:

```bash
make init-apisix
docker compose restart apisix
```

## ถูก rate-limit ตอน login

API จำกัด login ต่อ IP (เก็บใน Redis) ข้อความตอบกลับจะระบุเวลาที่ลองใหม่ได้ (retry-after)
ผู้ดูแลระบบ bootstrap ข้ามได้เมื่อ `ADMIN_BYPASS_RATE_LIMIT=true` หรือล้าง limit ด้วยการ restart:

```bash
make restart s=redis
```

## รีเซ็ตทุกอย่าง (ระวัง: ลบข้อมูล)

```bash
make clean        # ลบ container, network และ volume ทั้งหมด (DESTROYS DATA)
# หรือ
make teardown MODE=purge   # + ลบ secret ที่สร้างไว้ (.env, certs, keyfile)
```

จากนั้นติดตั้งใหม่ด้วย `make install`

## ดูเพิ่มเติม

- [installation.md](installation.md)
- [configuration.md](configuration.md)
- [backup-restore.md](backup-restore.md)
