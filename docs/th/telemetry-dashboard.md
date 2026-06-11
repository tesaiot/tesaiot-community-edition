# แดชบอร์ด Telemetry

แดชบอร์ด Telemetry คือส่วนแสดงผลข้อมูลอนุกรมเวลาที่ฝังอยู่ในหน้า **Device Details** ของ Admin UI
ใช้ดูค่า telemetry ที่อุปกรณ์ส่งเข้ามาในรูปแบบกราฟแบบ near real-time

## ตำแหน่งในระบบ

แดชบอร์ดอยู่ในหน้ารายละเอียดอุปกรณ์ของ Admin UI (React SPA, service `admin-ui`) ดึงข้อมูลจาก API
ซึ่งอ่านข้อมูลอนุกรมเวลาจาก TimescaleDB

```
อุปกรณ์ -> ingest (MQTT/HTTP) -> API -> TimescaleDB (hypertable)
หน้า Device Details -> API (dashboard service) -> TimescaleDB -> กราฟ
```

โค้ดฝั่ง API ที่ให้บริการข้อมูลแดชบอร์ดอยู่ที่ `services/api/api/services/dashboard/` และโมดูล
`services/api/api/modules/dashboard/`

## การไหลของข้อมูล telemetry

1. อุปกรณ์ส่ง telemetry ผ่าน MQTT (EMQX) หรือ HTTP (APISIX)
2. API/bridge เขียนข้อมูลลง TimescaleDB เป็น hypertable (และ MongoDB เมื่อ
   `ENABLE_DUAL_STORAGE=true`)
3. เมื่อเปิดหน้า Device Details, Admin UI เรียก API เพื่อ query ช่วงเวลาที่ต้องการ
4. ข้อมูลถูกแสดงเป็นกราฟอนุกรมเวลา

## ที่เก็บข้อมูล (TimescaleDB)

- ฐานข้อมูล: `tesa_telemetry` (ตั้งผ่าน `POSTGRES_DB`)
- โครงสร้างเริ่มต้นสร้างจาก `config/timescaledb/init-timescale.sql`
- schema อัตโนมัติเปิดด้วย `ENABLE_AUTO_TIMESCALE_SCHEMA=true`
- ใช้ hypertable เพื่อประสิทธิภาพในการ query ช่วงเวลา

## การใช้งาน

1. login เข้า Admin UI ที่ `https://localhost`
2. ไปที่หน้า Devices แล้วเลือกอุปกรณ์
3. ในหน้า Device Details จะเห็นส่วนแดชบอร์ด telemetry แสดงกราฟของ metric ต่าง ๆ
4. เลือกช่วงเวลา/metric ที่ต้องการดู

## การตรวจสอบข้อมูลด้วยมือ

ตรวจว่าข้อมูลเข้า TimescaleDB:

```bash
docker exec -it tesa-timescaledb \
  psql -U postgres -d tesa_telemetry -c "\dt"
```

ดูจำนวนแถวล่าสุด (ปรับชื่อตารางตามจริงจาก `\dt`):

```bash
docker exec -it tesa-timescaledb \
  psql -U postgres -d tesa_telemetry \
  -c "SELECT count(*) FROM telemetry;"
```

## การแก้ปัญหา

- ถ้ากราฟว่าง: ตรวจว่าอุปกรณ์ส่ง telemetry จริง (`make logs s=mqtt-bridge`, `make logs s=api`)
- ตรวจว่า TimescaleDB ทำงาน: `make health`
- ตรวจว่า ingest route ของ APISIX ตอบ (ดู [api-gateway-apisix.md](api-gateway-apisix.md))
- ตรวจ webhook auth ของ MQTT (ดู [mqtt-emqx.md](mqtt-emqx.md))

## ดูเพิ่มเติม

- [device-management.md](device-management.md)
- [mqtt-emqx.md](mqtt-emqx.md)
- [api-gateway-apisix.md](api-gateway-apisix.md)
