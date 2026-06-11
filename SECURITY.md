<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Security Policy

> เอกสารสองภาษา — เลื่อนลงด้านล่างสำหรับฉบับภาษาไทย ([ไปยังฉบับภาษาไทย](#นโยบายความปลอดภัย))

TESAIoT Community Edition issues and manages real X.509 device identities, runs a
private PKI, and brokers device telemetry. We take the security of the project
and its users seriously. This document explains which versions receive security
fixes and how to report a vulnerability **privately**.

---

## Supported versions

Security fixes are provided only for the latest released `1.x` minor line.
Older minor versions are expected to upgrade forward. TESAIoT Community Edition
follows [Semantic Versioning](https://semver.org/).

| Version  | Supported          |
|----------|--------------------|
| `1.x`    | :white_check_mark: Yes — security fixes provided |
| `< 1.0`  | :x: No — pre-release, upgrade to `1.x` |

The current released version is recorded in [`VERSION.txt`](VERSION.txt) and
[`CHANGELOG.md`](CHANGELOG.md). Always run the latest patch release of the
supported line before reporting an issue, in case it is already fixed.

---

## Reporting a vulnerability

**Do not** report security vulnerabilities through public GitHub issues,
Discussions, pull requests, or any other public channel. Public disclosure
before a fix is available puts every deployment at risk.

Instead, use one of the **private** channels below.

### Preferred: GitHub private vulnerability reporting

Use GitHub's built-in private advisory workflow:

1. Open the repository on GitHub.
2. Go to the **Security** tab.
3. Click **Report a vulnerability** (under *Advisories*).
4. Fill in the form. This opens a private channel visible only to you and the
   maintainers.

This is the preferred method because it keeps the report, discussion, and the
eventual fix coordinated in one private place.

### Alternative: private contact

If you cannot use GitHub private advisories, contact the maintainer privately
through the channel listed on the repository owner's GitHub profile
([@WiroonSriborrirux](https://github.com)). Clearly mark the message as a
**security report** so it is triaged accordingly. Do not include exploit
details in any public-facing field.

> Note: a dedicated `security@` mailbox is not bundled with this open-source
> distribution. Self-hosters who fork or operate this platform should publish
> their own security contact in this file for their downstream users.

### What to include

To help us triage and fix quickly, please include:

- The affected version (from `VERSION.txt`) and component
  (e.g. tesa-api, Vault PKI config, EMQX/APISIX config).
- A clear description of the vulnerability and its impact.
- Step-by-step reproduction instructions or a proof of concept.
- Any relevant configuration, logs (with secrets redacted), or environment
  details.
- Your assessment of severity, if you have one.

**Never** include real secrets, private keys, or production credentials in a
report. Redact them.

---

## Our process and your expectations

- **Acknowledgement:** we aim to acknowledge a valid report within **5 business
  days**.
- **Assessment:** we will confirm the issue, determine severity, and identify
  affected supported versions.
- **Fix & disclosure:** we follow **coordinated disclosure**. We will work on a
  fix privately, then release it and publish an advisory. We ask that you keep
  the report confidential until a fix is published.
- **Credit:** with your permission, we will credit you in the advisory and
  [`CHANGELOG.md`](CHANGELOG.md). You may also request to remain anonymous.

---

## Scope

This policy covers the code and configuration shipped in this CE
distribution (the `services/`, `config/`, `deploy/`, `scripts/` directories and
the Compose stack).

Vulnerabilities in **bundled third-party components** (listed in
[`NOTICE`](NOTICE) — e.g. Vault, EMQX, APISIX, MongoDB, TimescaleDB, nginx,
FastAPI, React) should be reported to those upstream projects. If a default
configuration we ship makes such a component insecure, that *is* in scope —
please report it here.

---

## Hardening reminders for operators

Self-hosters are responsible for the security of their own deployment. At a
minimum:

- Replace **all** generated default secrets in `.env` before any real use
  (`ADMIN_PASSWORD`, JWT secrets, database and broker credentials, Vault tokens).
- Never commit `.env`, certificates, or Vault tokens to version control
  (see [`.gitignore`](.gitignore)).
- Terminate TLS correctly and keep the PKI root key offline/sealed where
  possible.
- Keep Docker images and the host patched.

---
---

# นโยบายความปลอดภัย

> Bilingual document — for the English version scroll up
> ([go to English version](#security-policy)).

TESAIoT Community Edition ออกและจัดการอัตลักษณ์อุปกรณ์ X.509 ของจริง ใช้งาน PKI
ส่วนตัว และทำหน้าที่เป็นโบรกเกอร์ telemetry ของอุปกรณ์ เราจึงให้ความสำคัญกับ
ความปลอดภัยของโครงการและผู้ใช้งานอย่างจริงจัง เอกสารนี้อธิบายว่าเวอร์ชันใดบ้าง
ที่ได้รับการแก้ไขด้านความปลอดภัย และวิธี **รายงานช่องโหว่แบบเป็นความลับ**

---

## เวอร์ชันที่รองรับ

การแก้ไขด้านความปลอดภัยจะให้บริการเฉพาะสายเวอร์ชัน `1.x` ล่าสุดที่ปล่อยออกมา
เท่านั้น เวอร์ชันรองที่เก่ากว่าควรอัปเกรดขึ้นมาให้ทันสมัย โครงการนี้ใช้รูปแบบ
[Semantic Versioning](https://semver.org/)

| เวอร์ชัน | รองรับหรือไม่ |
|----------|----------------|
| `1.x`    | :white_check_mark: รองรับ — มีการแก้ไขด้านความปลอดภัย |
| `< 1.0`  | :x: ไม่รองรับ — เป็นรุ่นก่อนเผยแพร่ ให้อัปเกรดเป็น `1.x` |

เวอร์ชันปัจจุบันที่ปล่อยออกมาบันทึกไว้ในไฟล์ [`VERSION.txt`](VERSION.txt) และ
[`CHANGELOG.md`](CHANGELOG.md) ก่อนรายงานปัญหา โปรดอัปเดตเป็นแพตช์ล่าสุดของสาย
ที่รองรับเสมอ เผื่อว่าปัญหานั้นได้รับการแก้ไขไปแล้ว

---

## การรายงานช่องโหว่

**ห้าม** รายงานช่องโหว่ด้านความปลอดภัยผ่านช่องทางสาธารณะ ได้แก่ GitHub issues,
Discussions, pull requests หรือช่องทางสาธารณะอื่นใด การเปิดเผยต่อสาธารณะก่อนที่
จะมีการแก้ไข จะทำให้ทุกระบบที่ติดตั้งอยู่ตกอยู่ในความเสี่ยง

โปรดใช้ช่องทาง **เป็นความลับ** ด้านล่างนี้แทน

### ช่องทางที่แนะนำ: การรายงานช่องโหว่แบบส่วนตัวของ GitHub

ใช้ระบบ advisory แบบส่วนตัวที่มีมาในตัวของ GitHub

1. เปิดหน้า repository บน GitHub
2. ไปที่แท็บ **Security**
3. คลิก **Report a vulnerability** (ในส่วน *Advisories*)
4. กรอกแบบฟอร์ม ระบบจะเปิดช่องทางสื่อสารแบบส่วนตัวที่เห็นได้เฉพาะคุณและผู้ดูแล
   โครงการเท่านั้น

นี่คือวิธีที่แนะนำ เพราะเก็บทั้งรายงาน การพูดคุย และการแก้ไขไว้ในที่เดียวกัน
อย่างเป็นความลับ

### ทางเลือก: ติดต่อแบบส่วนตัว

หากไม่สามารถใช้ระบบ advisory ส่วนตัวของ GitHub ได้ ให้ติดต่อผู้ดูแลโครงการเป็น
การส่วนตัวผ่านช่องทางที่ระบุไว้ในโปรไฟล์ GitHub ของเจ้าของ repository
([@WiroonSriborrirux](https://github.com)) โปรดระบุให้ชัดเจนว่าข้อความนี้เป็น
**รายงานด้านความปลอดภัย (security report)** เพื่อให้ได้รับการจัดลำดับอย่าง
เหมาะสม และอย่าใส่รายละเอียดของการโจมตีในช่องข้อมูลที่เปิดเผยต่อสาธารณะ

> หมายเหตุ: ชุดแจกจ่ายโอเพนซอร์สนี้ไม่ได้แนบกล่องเมล `security@` มาให้
> ผู้ที่นำไป self-host หรือ fork ควรประกาศช่องทางติดต่อด้านความปลอดภัยของตนเอง
> ในไฟล์นี้สำหรับผู้ใช้ปลายทางของตน

### ข้อมูลที่ควรแนบมาด้วย

เพื่อช่วยให้เราจัดลำดับและแก้ไขได้รวดเร็ว โปรดแนบข้อมูลต่อไปนี้

- เวอร์ชันที่ได้รับผลกระทบ (จาก `VERSION.txt`) และส่วนประกอบที่เกี่ยวข้อง
  (เช่น tesa-api, ค่าตั้ง Vault PKI, ค่าตั้ง EMQX/APISIX)
- คำอธิบายช่องโหว่และผลกระทบอย่างชัดเจน
- ขั้นตอนการทำซ้ำ (reproduction) หรือ proof of concept
- ค่าตั้ง บันทึก log (ปิดบังความลับแล้ว) หรือรายละเอียดสภาพแวดล้อมที่เกี่ยวข้อง
- การประเมินระดับความรุนแรง หากคุณมี

**ห้าม** ใส่ความลับจริง กุญแจส่วนตัว หรือ credential ของระบบจริงลงในรายงาน
โปรดปิดบังข้อมูลเหล่านั้น

---

## กระบวนการของเราและสิ่งที่คุณคาดหวังได้

- **การตอบรับ:** เรามุ่งจะตอบรับรายงานที่ถูกต้องภายใน **5 วันทำการ**
- **การประเมิน:** เราจะยืนยันปัญหา ประเมินความรุนแรง และระบุเวอร์ชันที่รองรับ
  ซึ่งได้รับผลกระทบ
- **การแก้ไขและการเปิดเผย:** เราใช้แนวทาง **การเปิดเผยแบบประสานงาน (coordinated
  disclosure)** โดยจะแก้ไขเป็นการภายในก่อน แล้วจึงปล่อยการแก้ไขพร้อมประกาศ
  advisory เราขอให้คุณเก็บรายงานเป็นความลับจนกว่าการแก้ไขจะถูกเผยแพร่
- **การให้เครดิต:** หากคุณยินยอม เราจะให้เครดิตคุณใน advisory และใน
  [`CHANGELOG.md`](CHANGELOG.md) คุณสามารถขอไม่เปิดเผยตัวตนได้เช่นกัน

---

## ขอบเขต

นโยบายนี้ครอบคลุมโค้ดและค่าตั้งที่มาพร้อมในชุดแจกจ่าย Community Edition นี้ (ไดเรกทอรี
`services/`, `config/`, `deploy/`, `scripts/` และ Compose stack)

ช่องโหว่ใน **ส่วนประกอบของบุคคลที่สาม (third-party)** ที่แนบมา (ระบุไว้ใน
[`NOTICE`](NOTICE) เช่น Vault, EMQX, APISIX, MongoDB, TimescaleDB, nginx,
FastAPI, React) ควรรายงานไปยังโครงการต้นทางเหล่านั้นโดยตรง อย่างไรก็ตาม หากค่า
ตั้งเริ่มต้นที่เราแนบมาทำให้ส่วนประกอบเหล่านั้นไม่ปลอดภัย กรณีนี้ *อยู่ในขอบเขต*
โปรดรายงานมาที่นี่

---

## ข้อแนะนำการเสริมความแข็งแกร่งสำหรับผู้ดูแลระบบ

ผู้ที่นำไป self-host มีหน้าที่รับผิดชอบความปลอดภัยของระบบของตนเอง อย่างน้อยควร

- เปลี่ยนความลับเริ่มต้น **ทั้งหมด** ใน `.env` ก่อนใช้งานจริง
  (`ADMIN_PASSWORD`, JWT secret, credential ของฐานข้อมูลและโบรกเกอร์, Vault token)
- ห้าม commit ไฟล์ `.env`, ใบรับรอง หรือ Vault token เข้าสู่ระบบควบคุมเวอร์ชัน
  (ดู [`.gitignore`](.gitignore))
- ตั้งค่า TLS ให้ถูกต้อง และเก็บกุญแจ root ของ PKI ไว้แบบ offline/sealed
  เท่าที่เป็นไปได้
- อัปเดต Docker image และระบบปฏิบัติการของเครื่องโฮสต์ให้ทันสมัยเสมอ
