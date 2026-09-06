# TESAIoT Node-RED Integration Guide / คู่มือการเชื่อมต่อ TESAIoT ด้วย Node-RED

> 🇹🇭 โปรเจกต์นี้สาธิตการสร้าง Node-RED โหนดแบบโอเพ่นซอร์ส พร้อม FlowFuse Dashboard ที่ใช้สไตล์เดียวกับ TESAIoT Admin UI เพื่อดึงข้อมูลผ่าน APISIX API Gateway ได้ทันที
>
> 🇬🇧 This project shows how to build open-source friendly Node-RED nodes and FlowFuse Dashboard pages styled after the TESAIoT Admin UI, calling the platform through the APISIX API Gateway.

---

## 1. Project Layout / โครงสร้างโปรเจกต์

```
nodered-to-platform/
├── Dockerfile                  # 🇬🇧 Multi-stage build for reproducible images
├── README.md                   # 🇬🇧 This guide (TH/EN) / 🇹🇭 คู่มือฉบับนี้ (ไทย/อังกฤษ)
├── docker-compose.yml          # 🇬🇧 Sample stack with health-checks / 🇹🇭 docker-compose พร้อม health-check
├── package.json                # 🇬🇧 Node-RED project manifest / 🇹🇭 รายการ dependency และ custom nodes
├── settings.js                 # 🇬🇧 Runtime config (API defaults, admin path) / 🇹🇭 ตั้งค่า runtime, path `/admin`
├── tsconfig.json               # 🇬🇧 TypeScript compiler options / 🇹🇭 ตัวเลือก TypeScript
├── .env.example                # 🇬🇧 Copy to `.env` and fill API key / 🇹🇭 ตัวอย่างไฟล์ environment
├── run.sh                      # 🇬🇧 Bootstrap/build/start helper / 🇹🇭 สคริปต์ช่วยติดตั้งและรัน
├── flows/
│   └── tesaiot-flow.json       # 🇬🇧 Production-style dashboard / 🇹🇭 Flow สำหรับ Node-RED Dashboard
└── src/
    ├── lib/client.ts           # 🇬🇧 Axios client with TLS guards / 🇹🇭 client.ts ดูแล TLS และ error handling
    └── nodes/                  # 🇬🇧 Custom TESAIoT nodes / 🇹🇭 โหนดที่เขียนเอง
        ├── tesaiot-api-gateway.ts
        ├── tesaiot-device-lists.ts
        ├── tesaiot-device-profile.ts
        ├── tesaiot-device-data.ts
        └── tesaiot-api-usage.ts
```

---

## 2. Custom Node Blueprint / โครงสร้างโหนดเฉพาะทาง

- 🇹🇭 ทุกโหนดเขียนด้วย TypeScript และคอมไพล์เป็น `dist/nodes/*.js` พร้อมคำอธิบาย Why/What/How ในคอมเมนต์
- 🇬🇧 Each node is authored in TypeScript, compiled to `dist/nodes/*.js`, and heavily commented to explain Why/What/How for intermediate developers.
- 🇹🇭 โหนดไม่เก็บสถานะถาวร ค่าเชื่อมต่อทุกอย่างประกาศผ่าน message ที่รับเข้า ทำให้เข้าใจ flow ได้ง่าย
- 🇬🇧 Runtime is stateless: every input message describes the work, making debugging with the Node-RED sidebar trivial.
- 🇹🇭 config node (`tesaiot-api-gateway`) ใช้เก็บ API key และสร้าง Axios client พร้อม retry/backoff
- 🇬🇧 The config node caches an Axios client with retry/backoff so downstream nodes simply call `gatewayNode.getClient()`.

---

## 3. Getting Started / เริ่มใช้งาน

### 3.1 Local Development / รันบนเครื่องนักพัฒนา

1. 🇬🇧 `cp .env.example .env` then fill `TESAIOT_API_KEY` and optional overrides.
   🇹🇭 คัดลอก `.env.example` เป็น `.env` และกรอก `TESAIOT_API_KEY` พร้อมค่าอื่นถ้าต้องการ
2. 🇬🇧 Install dependencies: `./run.sh bootstrap`
   🇹🇭 ติดตั้ง dependency ด้วย `./run.sh bootstrap`
3. 🇬🇧 Build TypeScript nodes: `./run.sh build`
   🇹🇭 คอมไพล์โหนดด้วย `./run.sh build`
4. 🇬🇧 Start Node-RED: `./run.sh start`
   🇹🇭 รันเซิร์ฟเวอร์ Node-RED ผ่าน `./run.sh start`
5. 🇬🇧 Import `flows/tesaiot-flow.json` via the Node-RED editor or copy into `settings.js` flow path.
   🇹🇭 นำเข้า flow จาก `flows/tesaiot-flow.json` ผ่านหน้าเว็บ Node-RED หรือวางไว้ใน path ตาม `settings.js`

### 3.2 Docker Workflow / ใช้งานผ่าน Docker

1. 🇬🇧 Copy `.env.example` → `.env` and set credentials as above.
   🇹🇭 คัดลอก `.env.example` → `.env` แล้วตั้งค่าตามต้องการ
2. 🇬🇧 Build and launch: `./run.sh compose up`
   🇹🇭 สั่ง `./run.sh compose up` เพื่อ build และรันคอนเทนเนอร์ตัวอย่าง
3. 🇬🇧 Stop and clean: `./run.sh compose down`
   🇹🇭 ปิดและลบคอนเทนเนอร์ด้วย `./run.sh compose down`

---

## 4. Dashboard Walkthrough / แนะนำแดชบอร์ด

| Section | 🇹🇭 รายละเอียด | 🇬🇧 Description |
| --- | --- | --- |
| Device Snapshot | สรุปจำนวนอุปกรณ์ สถานะ และตารางย่อย 25 รายการแรก | Displays device totals and the first 25 rows for quick health checks |
| Device Profile | แสดงข้อมูลเชิงลึกของอุปกรณ์แรกในลิสต์ (ชื่อ, สถานะ, ชนิด, ความปลอดภัย) | Shows profile fields for the first device in the list |
| Device Telemetry | สร้างค่าเฉลี่ยและตารางล่าสุดจาก TimescaleDB (heart rate, temp, SpO₂) | Renders moving averages and a recent-history table |
| API Usage | แจ้งจำนวนคำขอ API ต่อนาที, อัตรา TLS, และเวลา telemetry ล่าสุด | Reports API request/minute, secure fleet percentage, and last telemetry timestamp |

> 🇹🇭 หากต้องการปรับสไตล์ สามารถแก้ไข `theme/custom.css` ซึ่งใช้แนวคิด Tailwind ที่ย่อไว้เป็น CSS ปกติ
>
> 🇬🇧 Styling tweaks live in `theme/custom.css`, keeping Tailwind-inspired tokens available without requiring the Tailwind toolchain.

---

## 5. Troubleshooting / การแก้ปัญหา

- 🇬🇧 **gRPC/WebSocket issues** – ensure ports 1880 (Node-RED) and 1883/8883 (MQTT) are reachable; the flow defaults to the production endpoints.
  🇹🇭 หาก dashboard ไม่แสดงข้อมูล ตรวจสอบให้แน่ใจว่าเชื่อมต่อพอร์ต 1880, 1883/8883 ได้ และ API key ถูกต้อง
- 🇬🇧 **Flow remains blank** – re-import `tesaiot-flow.json` after pulling updates; the `ui-template` widgets rely on `msg.payload`.
  🇹🇭 ถ้าแดชบอร์ดยังว่าง ให้ import flow ใหม่ เพราะ `ui-template` จะเรนเดอร์ HTML จาก `msg.payload`
- 🇬🇧 **TypeScript build fails** – run `npm install` again and confirm Node ≥ 18.18; the repo uses `esbuild` within the build script.
  🇹🇭 หาก build ไม่ผ่าน ให้รัน `npm install` และตรวจสอบว่า Node เวอร์ชัน ≥ 18.18

---

## 6. Further Reading / แหล่งอ่านเพิ่มเติม

- 🇬🇧 [Node-RED Creating Nodes](https://nodered.org/docs/creating-nodes/) – official guide for packaging custom nodes
  🇹🇭 เอกสารทางการของ Node-RED สำหรับสร้างและเผยแพร่โหนดใหม่
- 🇬🇧 [FlowFuse Dashboard Docs](https://dashboard.flowfuse.com/) – component reference and layout best practices
  🇹🇭 สารานุกรม component ของ FlowFuse พร้อมตัวอย่างการจัดเลย์เอาต์
- The Admin UI of your own Community Edition install (`https://localhost/` by
  default) – authenticate there to download the credential bundles this sample uses
  🇹🇭 เข้าระบบ TESAIoT Admin UI เพื่อดาวน์โหลด credential bundle สำหรับใช้งานกับตัวอย่างนี้

---

> 🇹🇭 หากพบปัญหาหรืออยากเพิ่มฟีเจอร์ แนะนำให้สร้าง branch ใหม่แล้วส่ง pull request
>
> 🇬🇧 Contributions are welcome—open an issue or PR if you spot improvements.
