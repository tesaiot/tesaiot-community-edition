# คู่มือการเชื่อมต่อ TESAIoT ด้วย Node-RED

> **ภาษาไทย** - สำหรับเวอร์ชันภาษาอังกฤษ ดูที่ [README.md](README.md)

โปรเจกต์นี้สาธิตการสร้าง Node-RED โหนดแบบโอเพ่นซอร์ส พร้อม FlowFuse Dashboard ที่ใช้สไตล์เดียวกับ TESAIoT Admin UI เพื่อดึงข้อมูลผ่าน APISIX API Gateway ได้ทันที

---

## 1. โครงสร้างโปรเจกต์

```
nodered-to-platform/
├── Dockerfile                  # Multi-stage build สำหรับ image ที่ทำซ้ำได้
├── README.md                   # คู่มือภาษาอังกฤษ
├── README-TH.md                # คู่มือฉบับนี้ (ไทย)
├── docker-compose.yml          # docker-compose พร้อม health-check
├── package.json                # รายการ dependency และ custom nodes
├── settings.js                 # ตั้งค่า runtime, path `/admin`
├── tsconfig.json               # ตัวเลือก TypeScript
├── .env.example                # ตัวอย่างไฟล์ environment
├── run.sh                      # สคริปต์ช่วยติดตั้งและรัน
├── flows/
│   └── tesaiot-flow.json       # Flow สำหรับ Node-RED Dashboard
└── src/
    ├── lib/client.ts           # client.ts ดูแล TLS และ error handling
    └── nodes/                  # โหนดที่เขียนเอง
        ├── tesaiot-api-gateway.ts
        ├── tesaiot-device-lists.ts
        ├── tesaiot-device-profile.ts
        ├── tesaiot-device-data.ts
        └── tesaiot-api-usage.ts
```

---

## 2. โครงสร้างโหนดเฉพาะทาง

- ทุกโหนดเขียนด้วย TypeScript และคอมไพล์เป็น `dist/nodes/*.js` พร้อมคำอธิบาย Why/What/How ในคอมเมนต์
- โหนดไม่เก็บสถานะถาวร ค่าเชื่อมต่อทุกอย่างประกาศผ่าน message ที่รับเข้า ทำให้เข้าใจ flow ได้ง่าย
- config node (`tesaiot-api-gateway`) ใช้เก็บ API key และสร้าง Axios client พร้อม retry/backoff

---

## 3. เริ่มใช้งาน

### 3.1 รันบนเครื่องนักพัฒนา

1. คัดลอก `.env.example` เป็น `.env` และกรอก `TESAIOT_API_KEY` พร้อมค่าอื่นถ้าต้องการ
2. ติดตั้ง dependency ด้วย `./run.sh bootstrap`
3. คอมไพล์โหนดด้วย `./run.sh build`
4. รันเซิร์ฟเวอร์ Node-RED ผ่าน `./run.sh start`
5. นำเข้า flow จาก `flows/tesaiot-flow.json` ผ่านหน้าเว็บ Node-RED หรือวางไว้ใน path ตาม `settings.js`

### 3.2 ใช้งานผ่าน Docker

1. คัดลอก `.env.example` → `.env` แล้วตั้งค่าตามต้องการ
2. สั่ง `./run.sh compose up` เพื่อ build และรันคอนเทนเนอร์ตัวอย่าง
3. ปิดและลบคอนเทนเนอร์ด้วย `./run.sh compose down`

---

## 4. แนะนำแดชบอร์ด

| Section | รายละเอียด |
| --- | --- |
| Device Snapshot | สรุปจำนวนอุปกรณ์ สถานะ และตารางย่อย 25 รายการแรก |
| Device Profile | แสดงข้อมูลเชิงลึกของอุปกรณ์แรกในลิสต์ (ชื่อ, สถานะ, ชนิด, ความปลอดภัย) |
| Device Telemetry | สร้างค่าเฉลี่ยและตารางล่าสุดจาก TimescaleDB (heart rate, temp, SpO₂) |
| API Usage | แจ้งจำนวนคำขอ API ต่อนาที, อัตรา TLS, และเวลา telemetry ล่าสุด |

> หากต้องการปรับสไตล์ สามารถแก้ไข `theme/custom.css` ซึ่งใช้แนวคิด Tailwind ที่ย่อไว้เป็น CSS ปกติ

---

## 5. การแก้ปัญหา

- หาก dashboard ไม่แสดงข้อมูล ตรวจสอบให้แน่ใจว่าเชื่อมต่อพอร์ต 1880, 1883/8883 ได้ และ API key ถูกต้อง
- ถ้าแดชบอร์ดยังว่าง ให้ import flow ใหม่ เพราะ `ui-template` จะเรนเดอร์ HTML จาก `msg.payload`
- หาก build ไม่ผ่าน ให้รัน `npm install` และตรวจสอบว่า Node เวอร์ชัน ≥ 18.18

---

## 6. แหล่งอ่านเพิ่มเติม

- [Node-RED Creating Nodes](https://nodered.org/docs/creating-nodes/) – เอกสารทางการของ Node-RED สำหรับสร้างและเผยแพร่โหนดใหม่
- [FlowFuse Dashboard Docs](https://dashboard.flowfuse.com/) – สารานุกรม component ของ FlowFuse พร้อมตัวอย่างการจัดเลย์เอาต์
- [TESAIoT Admin UI](https://admin.tesaiot.com/) – เข้าระบบ TESAIoT Admin UI เพื่อดาวน์โหลด credential bundle สำหรับใช้งานกับตัวอย่างนี้

---

> หากพบปัญหาหรืออยากเพิ่มฟีเจอร์ แนะนำให้สร้าง branch ใหม่แล้วส่ง pull request
