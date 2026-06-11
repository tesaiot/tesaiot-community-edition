# การจัดการผู้ใช้

TESAIoT Community Edition มีระบบบัญชีผู้ใช้ภายในสำหรับองค์กรเดียว รองรับการสร้างผู้ใช้ บทบาท (role)
การยืนยันตัวตน และการรีเซ็ตรหัสผ่าน

## ผู้ดูแลระบบเริ่มต้น (bootstrap admin)

ตอน boot ครั้งแรก API สร้างบัญชี admin จากตัวแปรใน `.env`:

```
ADMIN_EMAIL=admin@localhost
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGEME_ADMIN_PASSWORD
```

ใช้บัญชีนี้ login เข้า Admin UI ที่ `https://localhost` ครั้งแรก จากนั้นควรเปลี่ยนรหัสผ่านและ
สร้างผู้ใช้เพิ่มตามต้องการ

## การยืนยันตัวตน

- รหัสผ่านถูก hash ด้วย **bcrypt** โดย cost factor มาจาก `BCRYPT_LOG_ROUNDS` (ค่าเริ่มต้น 12)
- หลัง login สำเร็จ API ออก **JWT** เซ็นด้วย `JWT_SECRET` (HS256)
- ไคลเอนต์แนบ JWT ในส่วน `Authorization: Bearer <token>` สำหรับการเรียก API ต่อไป

### Rate limit การ login

การ login ถูกจำกัดความถี่ต่อ IP โดยเก็บสถานะใน Redis ผู้ดูแลระบบ bootstrap สามารถข้ามได้เมื่อ
ตั้ง `ADMIN_BYPASS_RATE_LIMIT=true`

> เมื่อถูก rate-limit ระบบจะแจ้งเวลาที่ลองใหม่ได้ (retry-after) ไม่ใช่เพียงข้อความทั่วไป

## บทบาท (Roles)

ระบบ role ใช้แบ่งสิทธิ์การเข้าถึง เช่น ผู้ดูแล (admin) กับผู้ใช้ทั่วไป (user) บทบาทจะถูกตรวจที่
middleware ของ API ก่อนเข้าถึง resource ที่ต้องการสิทธิ์

ในฉบับ Community Edition ผู้ใช้ทั้งหมดอยู่ในองค์กรเดียว (`DEFAULT_ORG_ID`) — ไม่มีการแยกข้ามองค์กร

## การสร้าง / จัดการผู้ใช้

จาก Admin UI:

1. login ด้วยบัญชี admin
2. ไปที่หน้าจัดการผู้ใช้ (User Management)
3. สร้างผู้ใช้ใหม่: กรอกอีเมล ชื่อผู้ใช้ บทบาท
4. ระบบสามารถส่งอีเมลเชิญ/ตั้งรหัสผ่าน (เมื่อเปิด `EMAIL_ENABLED=true`)

หากตั้ง `EMAIL_ENABLED=false` (ค่าเริ่มต้น) อีเมลจะถูก log ออก stdout แทนการส่งจริง เหมาะกับการ
ทดสอบ — ดู log ได้ด้วย `make logs s=api`

## OTP / รีเซ็ตรหัสผ่าน

ระบบรองรับ OTP สำหรับยืนยันตัวตน/รีเซ็ตรหัสผ่าน ควบคุมด้วยตัวแปร:

```
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=15
OTP_MAX_ATTEMPTS=3
OTP_COOLDOWN_SECONDS=30
```

OTP จะถูกส่งผ่านช่องทางอีเมลที่ตั้งค่าไว้ (SMTP หรือ Resend)

## บัญชีบริการสำหรับ MQTT bridge

telemetry bridge ต้อง login เข้า API เพื่อ forward telemetry โดยใช้บัญชีที่ระบุใน:

```
BRIDGE_API_USER=admin@localhost
BRIDGE_API_PASSWORD=CHANGEME_ADMIN_PASSWORD
```

บัญชีนี้ต้องมีอยู่จริงในทะเบียนผู้ใช้ แนะนำให้สร้างบัญชีบริการแยกแทนการใช้ admin ใน production

## ที่เก็บข้อมูล

ข้อมูลผู้ใช้ทั้งหมดเก็บใน MongoDB (`MONGODB_DATABASE`, ค่าเริ่มต้น `tesa_iot`) โครงสร้างถูกสร้าง
ครั้งแรกโดย `config/mongodb/init-mongo.js`

## ดูเพิ่มเติม

- [configuration.md](configuration.md) — ตัวแปรที่เกี่ยวกับ auth/JWT/admin
- [device-management.md](device-management.md) — การจัดการอุปกรณ์และ identity
