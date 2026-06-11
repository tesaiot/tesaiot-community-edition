# API Gateway (APISIX)

APISIX เป็นเกตเวย์ขอบ (edge gateway) ที่จัดเส้นทางและป้องกัน API ของแพลตฟอร์ม โดยเฉพาะช่องทาง
ingest telemetry จากอุปกรณ์ ในฉบับ Community Edition APISIX ทำงานในโหมด **standalone YAML** จึง
**ไม่ต้องใช้ etcd**

## พอร์ต

```
9080   HTTP
9443   HTTPS / serverTLS / mTLS
9180   Admin API
```

## ไฟล์ตั้งค่า

| ไฟล์ | บทบาท |
|---|---|
| `config/apisix/config.yaml` | ตั้งค่าหลัก + admin key |
| `config/apisix/apisix.yaml` | declarative resources: SSL, routes, consumers (โหลดตอน boot) |
| `config/apisix/mtls-routes.yaml` | ตัวอย่าง route แบบ mTLS |
| `config/apisix/README.md` | บันทึกประกอบ |

เพราะอยู่ในโหมด standalone YAML, route และ consumer ใน `apisix.yaml` จะถูกโหลดตอน boot
ไม่ต้อง push ผ่าน Admin API

## การ provision admin key

```bash
make init-apisix
```

`init-apisix-routes.sh` จะ:

1. ฉีด `APISIX_ADMIN_KEY` จาก `.env` ลงใน `config/apisix/config.yaml`
2. ตรวจสอบว่า gateway ทำงานและเสิร์ฟ route ที่ประกาศไว้

หลัง sync admin key ครั้งแรก ต้อง restart:

```bash
docker compose restart apisix
```

## Route ที่ติดตั้งมาให้

### telemetry ingest (IP-based)

```yaml
- id: "device-telemetry-ip"
  uri: "/api/v1/telemetry"
  methods: ["POST", "OPTIONS"]
  upstream:
    nodes:
      "tesa-api:5566": 1
  plugins:
    key-auth:
      header: "X-API-Key"
      query: "api_key"
      hide_credentials: true
    limit-req:
      rate: 1000
      burst: 2000
      key: "consumer_name"
      rejected_code: 429
      rejected_msg: "Rate limit exceeded"
    cors:
      allow_origin: "*"
```

### telemetry ingest (device-scoped)

```yaml
- id: "device-telemetry-device-id"
  uri: "/api/v1/devices/*/telemetry"
  methods: ["POST", "OPTIONS"]
  upstream:
    nodes:
      "tesa-api:5566": 1
```

## ปลั๊กอินที่ใช้

| ปลั๊กอิน | หน้าที่ |
|---|---|
| `key-auth` | ยืนยันตัวตนด้วย API key ผ่าน header `X-API-Key` หรือ query `api_key` |
| `limit-req` | จำกัดอัตราการเรียก (rate=1000, burst=2000) คืน 429 พร้อมข้อความเมื่อเกิน — ใน standalone YAML mode เป็นลิมิตระดับ route (แชร์ร่วมกันทุก caller) ไม่ใช่โควต้าต่ออุปกรณ์ ส่วนลิมิตต่ออุปกรณ์จริงบังคับใช้โดย API backend |
| `cors` | จัดการ CORS preflight |
| `response-rewrite` | เพิ่ม header การตอบกลับ |

## Consumer (API key ของอุปกรณ์)

การ ingest ผ่าน HTTP ใช้ปลั๊กอิน `key-auth` ตรวจ API key ใน standalone YAML mode
consumer เป็นแบบ static (โหลดจาก `apisix.yaml` ตอน boot; ไฟล์ mount แบบ read-only และ
Admin API แก้ runtime state ไม่ได้) มี consumer ตัวอย่างเพียงตัวเดียว — **ไม่มี** การลงทะเบียน
consumer ต่ออุปกรณ์แบบ dynamic. API key จริงต่ออุปกรณ์ออกและตรวจสอบโดย API backend
(`api_key_service.py`) ไม่ใช่ลงทะเบียนเป็น APISIX consumer. หากต้องการ per-device consumer
ที่ gateway จริง ต้องรัน APISIX แบบ etcd control plane (อยู่นอกขอบเขตของ CE)

## serverTLS / mTLS ที่ gateway

- **serverTLS** — ใบรับรองเซิร์ฟเวอร์เก็บในบล็อก `ssls` ของ `apisix.yaml` (ดู [security-tls-mtls.md](security-tls-mtls.md))
- **mTLS** — เพิ่มบล็อก `client` พร้อม `ca` + `depth` และตั้ง `verify_client: true` ดูตัวอย่างใน `mtls-routes.yaml`

## ตรวจสอบ

```bash
make logs s=apisix
curl -i http://localhost:9080/         # ตรวจว่า gateway ตอบ
```

ทดสอบ ingest:

```bash
curl -k -X POST https://localhost:9443/api/v1/telemetry \
  -H "X-API-Key: <device-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 25.4}'
```

## ดูเพิ่มเติม

- [security-tls-mtls.md](security-tls-mtls.md)
- [device-management.md](device-management.md)
- [telemetry-dashboard.md](telemetry-dashboard.md)
