<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Getting Support

> เอกสารสองภาษา — เลื่อนลงด้านล่างสำหรับฉบับภาษาไทย ([ไปยังฉบับภาษาไทย](#การขอความช่วยเหลือ))

Thanks for using **TESAIoT Community Edition** — an Apache-2.0, self-host,
single-organization distribution. This page tells you where to get help so your
question reaches the right place.

## Before you ask

Most usage questions are already answered in the documentation. Please check
these first:

- **Documentation (English):** [`docs/en/`](docs/en/)
  - [installation.md](docs/en/installation.md) — install and bring the stack up.
  - [configuration.md](docs/en/configuration.md) — environment and config.
  - [user-management.md](docs/en/user-management.md)
  - [device-management.md](docs/en/device-management.md)
  - [security-tls-mtls.md](docs/en/security-tls-mtls.md)
  - [certificate-lifecycle.md](docs/en/certificate-lifecycle.md)
  - [api-gateway-apisix.md](docs/en/api-gateway-apisix.md)
  - [mqtt-emqx.md](docs/en/mqtt-emqx.md)
  - [telemetry-dashboard.md](docs/en/telemetry-dashboard.md)
  - [troubleshooting.md](docs/en/troubleshooting.md) — common problems and fixes.
  - [upgrade.md](docs/en/upgrade.md) and [backup-restore.md](docs/en/backup-restore.md)
- **Documentation (Thai):** [`docs/th/`](docs/th/) — the same topics in Thai.

## How to get help

| You want to… | Go here |
| --- | --- |
| Ask a usage / "how do I…" question | [GitHub Discussions](https://github.com/tesaiot/tesaiot-community-edition/discussions) |
| Report a reproducible bug or request a feature | [Open an issue](https://github.com/tesaiot/tesaiot-community-edition/issues) using the templates in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) |
| Report a security vulnerability | **Do not** open a public issue — follow [SECURITY.md](SECURITY.md) |
| Contribute code or docs | Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |

## Writing a good question

To get a fast, useful answer, please include:

- What you were trying to do and what happened instead.
- The version / commit of TESAIoT Community Edition you are running.
- Your environment (OS, Docker / Docker Compose versions).
- Relevant logs or error output (redact any secrets, tokens, or keys first).
- The minimal steps to reproduce the problem.

## Scope reminder

This is a single-organization, self-host distribution covering eight
capabilities: user management; device / identity management; serverTLS and mTLS
authentication; certificate life-cycle via HashiCorp Vault PKI; the APISIX API
gateway; the EMQX MQTT broker; MongoDB and TimescaleDB; and the IoT telemetry
dashboard. Questions about features that are intentionally out of scope
(multi-tenancy, AI inference, OTA / firmware update, B2B features, third-party
services, analytics) are unlikely to be supported here.

---

# การขอความช่วยเหลือ

ขอบคุณที่ใช้งาน **TESAIoT Community Edition** — ดิสทริบิวชันแบบ self-host สำหรับ
องค์กรเดียว ภายใต้สัญญาอนุญาต Apache-2.0 หน้านี้จะบอกว่าคุณควรขอความช่วยเหลือ
ที่ใด เพื่อให้คำถามของคุณไปถึงช่องทางที่เหมาะสม

## ก่อนถามคำถาม

คำถามการใช้งานส่วนใหญ่มีคำตอบอยู่ในเอกสารแล้ว กรุณาตรวจสอบสิ่งเหล่านี้ก่อน:

- **เอกสาร (ภาษาอังกฤษ):** [`docs/en/`](docs/en/)
- **เอกสาร (ภาษาไทย):** [`docs/th/`](docs/th/) — หัวข้อเดียวกันในภาษาไทย เช่น
  การติดตั้ง การตั้งค่า การจัดการผู้ใช้ การจัดการอุปกรณ์ TLS/mTLS วงจรชีวิต
  ใบรับรอง APISIX EMQX แดชบอร์ด และการแก้ปัญหา

## ช่องทางขอความช่วยเหลือ

| คุณต้องการ… | ไปที่ |
| --- | --- |
| ถามคำถามการใช้งาน / "ทำอย่างไร…" | [GitHub Discussions](https://github.com/tesaiot/tesaiot-community-edition/discussions) |
| รายงานบั๊กที่ทำซ้ำได้ หรือเสนอฟีเจอร์ | [เปิด issue](https://github.com/tesaiot/tesaiot-community-edition/issues) โดยใช้เทมเพลตใน [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) |
| รายงานช่องโหว่ด้านความปลอดภัย | **อย่า** เปิด issue สาธารณะ — ดู [SECURITY.md](SECURITY.md) |
| ร่วมพัฒนาโค้ดหรือเอกสาร | อ่าน [CONTRIBUTING.md](CONTRIBUTING.md) และ [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |

## การเขียนคำถามที่ดี

เพื่อให้ได้คำตอบที่รวดเร็วและเป็นประโยชน์ กรุณาระบุ:

- สิ่งที่คุณพยายามทำ และผลลัพธ์ที่เกิดขึ้นจริง
- เวอร์ชัน / commit ของ TESAIoT Community Edition ที่คุณใช้งาน
- สภาพแวดล้อมของคุณ (ระบบปฏิบัติการ เวอร์ชัน Docker / Docker Compose)
- ล็อกหรือข้อความแสดงข้อผิดพลาดที่เกี่ยวข้อง (ลบความลับ โทเคน หรือคีย์ออกก่อน)
- ขั้นตอนการทำซ้ำปัญหาแบบสั้นที่สุด

## ขอบเขตของโครงการ

นี่คือดิสทริบิวชันแบบ self-host สำหรับองค์กรเดียว ครอบคลุมแปดความสามารถ ได้แก่
การจัดการผู้ใช้; การจัดการอุปกรณ์ / อัตลักษณ์; การยืนยันตัวตนแบบ serverTLS และ
mTLS; การจัดการวงจรชีวิตใบรับรองผ่าน HashiCorp Vault PKI; API gateway APISIX;
MQTT broker EMQX; MongoDB และ TimescaleDB; และแดชบอร์ด IoT telemetry คำถามเกี่ยว
กับฟีเจอร์ที่อยู่นอกขอบเขตโดยตั้งใจ (multi-tenancy, AI inference, OTA / การอัปเดต
เฟิร์มแวร์, ฟีเจอร์ B2B, บริการภายนอก, analytics) อาจไม่ได้รับการสนับสนุนที่นี่
