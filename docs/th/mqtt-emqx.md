# MQTT Broker (EMQX)

EMQX เป็นโบรกเกอร์ MQTT สำหรับรับ telemetry และคำสั่งควบคุมจากอุปกรณ์ IoT รองรับทั้ง serverTLS
และ mTLS โดยการยืนยันตัวตนและ ACL ตรวจผ่าน webhook ของ API

## พอร์ต

```
1883    MQTT plain (สำหรับ local/dev เท่านั้น)
8883    MQTT mTLS
8884    MQTT serverTLS
8083    MQTT over WebSocket (WS)
8084    MQTT over WebSocket Secure (WSS)
18083   Web dashboard
```

> ใน production แนะนำให้ปิดพอร์ต 1883 และใช้ 8883 (mTLS) หรือ 8884 (serverTLS)

## ไฟล์ตั้งค่า

| ไฟล์ | บทบาท |
|---|---|
| `config/emqx/emqx.conf` | ตั้งค่าหลักของ broker |
| `config/emqx/acl.conf` | กฎ ACL |
| `config/emqx/auth-built-in-db-bootstrap.csv` | user ภายในเริ่มต้น (bootstrap) |

ใบรับรองเซิร์ฟเวอร์ถูก mount จาก volume `emqx-certs` (vault-agent เป็นผู้ render)

## Dashboard

เข้าใช้งานที่ `http://localhost:18083`

```
username: admin
password: <ค่าจาก EMQX_DASHBOARD_PASSWORD ใน .env>
```

## การยืนยันตัวตนและ ACL

EMQX ตรวจสอบสิทธิ์ผ่าน webhook ที่เรียกกลับมายัง API:

```
อุปกรณ์เชื่อมต่อ -> EMQX -> POST webhook auth/ACL -> API -> อนุญาต/ปฏิเสธ
```

EMQX แนบ bearer secret จาก `EMQX_WEBHOOK_SECRET` ในการเรียก webhook เพื่อให้ API ยืนยันว่าเป็น
คำขอจาก broker จริง

สำหรับ mTLS, CN ในใบรับรองไคลเอนต์จะถูกใช้กำหนด identity ของอุปกรณ์ และ ACL จะตรวจว่าอุปกรณ์มี
สิทธิ์ publish/subscribe ใน topic ใด

## ผู้ใช้ภายใน (built-in users)

`init-emqx.sh` provision ผู้ใช้ภายในที่ telemetry bridge ใช้เชื่อมต่อ:

```bash
make init-emqx
```

ผู้ใช้ `mqtt-bridge` ใช้รหัสผ่านจาก `MQTT_BRIDGE_PASSWORD` และผู้ใช้ `mqtt_user` ใช้
`MQTT_PASSWORD`

## Telemetry bridge

service `mqtt-bridge` subscribe topic telemetry จาก EMQX แล้ว forward เข้า API เพื่อเก็บลง
TimescaleDB/MongoDB เชื่อมต่อ EMQX ภายในผ่านพอร์ต 8884 (serverTLS, ตรวจสอบใบรับรอง broker กับ CA bundle ที่ vault-agent render) ด้วยผู้ใช้
`mqtt-bridge` และ login เข้า API ด้วยบัญชี `BRIDGE_API_USER`

```
EMQX (8884 serverTLS ภายใน) -> mqtt-bridge -> API (5566 ภายใน) -> TimescaleDB / MongoDB
```

## การ publish telemetry

### serverTLS (พอร์ต 8884)

```bash
mosquitto_pub \
  -h localhost -p 8884 \
  --cafile ca-bundle.pem \
  -u <device-username> -P <device-password> \
  -t "devices/dev-001/telemetry" \
  -m '{"temp": 25.4}'
```

### mTLS (พอร์ต 8883)

```bash
mosquitto_pub \
  -h localhost -p 8883 \
  --cafile ca-bundle.pem \
  --cert device-cert.pem \
  --key device-key.pem \
  -t "devices/dev-001/telemetry" \
  -m '{"temp": 25.4}'
```

## ตรวจสอบ

```bash
make logs s=emqx
docker exec tesa-emqx emqx ctl status
docker exec tesa-emqx emqx ctl listeners      # ดู listener และพอร์ต
```

## ดูเพิ่มเติม

- [security-tls-mtls.md](security-tls-mtls.md)
- [device-management.md](device-management.md)
- [telemetry-dashboard.md](telemetry-dashboard.md)
