<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Project Governance / การกำกับดูแลโครงการ

This document describes how **TESAIoT Community Edition** is governed: who makes
decisions, what the roles are, and how those decisions get made. It is written
to be lightweight and practical for a small, single-organization open-source
project.

> เอกสารนี้มีทั้งฉบับภาษาอังกฤษ (ด้านบน) และฉบับภาษาไทย (ด้านล่าง) —
> ดู [ฉบับภาษาไทย](#th) ได้ที่ส่วนท้ายของไฟล์

---

## English

### 1. Mission and scope

TESAIoT Community Edition is an Apache-2.0, self-hostable, **single-organization**
distribution of the TESAIoT Secure IoT Platform. Governance exists to keep the
project healthy, in scope, and welcoming to contributors.

The project deliberately ships only the 8 capabilities listed in
[CONTRIBUTING.md → Project scope](CONTRIBUTING.md#project-scope). Governance
decisions must respect that scope: multi-tenancy, AI inference, OTA, B2B, and
other excluded features are out of scope by design.

### 2. Roles

The project recognizes three roles. Anyone can move "up" through sustained,
high-quality contribution; roles carry responsibilities, not privileges.

| Role | Who they are | What they do |
|---|---|---|
| **Contributor** | Anyone who opens an issue or pull request, improves docs, triages, or reviews. | Propose changes, report bugs, help others. No special permissions required. |
| **Maintainer** | A contributor with a sustained track record who has been granted write access. | Review and merge PRs, triage issues, cut releases, uphold scope and the Code of Conduct. |
| **Project Steward (BDFL-delegate)** | The project owner / lead maintainer. | Final tie-breaker on contested decisions, manages maintainer membership, owns security disclosure and licensing decisions. |

The current **Project Steward** is the original author and copyright steward of
the upstream platform (see [NOTICE](NOTICE)). The Steward may delegate any
responsibility to maintainers.

### 3. Becoming a maintainer

A contributor may be invited to become a maintainer after demonstrating:

- A sustained history of merged, high-quality contributions.
- Sound code review and good judgment on scope.
- Adherence to the [Code of Conduct](CODE_OF_CONDUCT.md) and the
  [coding standards](CONTRIBUTING.md#coding-standards).

Any existing maintainer may nominate a contributor. The nomination is approved
by **lazy consensus** among current maintainers (see below). Maintainers who
become inactive for an extended period (typically ~6 months) may be moved to
emeritus status by the Steward; emeritus maintainers can be reinstated on
request.

### 4. How decisions are made

The project uses **lazy consensus** as its default decision process:

1. A change is proposed publicly (issue, discussion, or pull request).
2. Maintainers and contributors have a reasonable review window (typically a
   few days; longer for large or breaking changes).
3. If **no maintainer objects**, the proposal is considered accepted and may be
   merged once CI is green and at least one maintainer has approved.
4. If there is **disagreement**, the proposers and objectors work toward a
   compromise in the open.
5. If consensus cannot be reached, any maintainer may call for a vote.

**Voting.** When a vote is needed, each maintainer has one vote. A simple
majority of votes cast within the voting window decides the matter. The
**Project Steward** breaks ties and may, in rare cases, veto a decision that
would take the project out of scope, violate its license, or harm its security
posture — with a public explanation.

**Routine changes** (typo fixes, docs, small bug fixes, dependency bumps) need
only one maintainer approval and green CI — no broader process required.

### 5. Changes to governance, license, or scope

The following require explicit Steward approval and should be discussed openly
before being merged:

- Changing this governance model.
- Changing the project license or the [NOTICE](NOTICE) attribution.
- Adding or removing a capability from the
  [project scope](CONTRIBUTING.md#project-scope).
- Reintroducing any of the documented hard exclusions (multi-tenancy, AI
  inference, OTA, B2B / WebSocket, etc.).

### 6. Code of Conduct and security

All participants — including maintainers and the Steward — are bound by the
[Code of Conduct](CODE_OF_CONDUCT.md). Security vulnerabilities follow the
coordinated disclosure process in [SECURITY.md](SECURITY.md) and are handled by
the Steward and maintainers, never in public issues.

### 7. Releases

Maintainers cut releases following [Semantic Versioning](https://semver.org)
and record them in the [CHANGELOG](CHANGELOG.md). The Steward signs off on
releases that change the license, scope, or security-relevant behavior.

---

<a id="th"></a>

## ภาษาไทย (Thai)

### 1. พันธกิจและขอบเขต

TESAIoT Community Edition เป็นชุดแจกจ่ายแบบโอเพนซอร์สภายใต้สัญญาอนุญาต Apache-2.0
สำหรับการติดตั้งใช้งานเองในรูปแบบ **องค์กรเดียว (single-organization)** ซึ่งสกัดมาจาก
TESAIoT Secure IoT Platform ฉบับเต็ม การกำกับดูแล (governance) มีไว้เพื่อรักษาให้
โครงการมีสุขภาพดี อยู่ในขอบเขตที่กำหนด และเปิดรับผู้ร่วมพัฒนา

โครงการนี้แจกจ่ายเฉพาะ 8 ความสามารถที่ระบุไว้ใน
[CONTRIBUTING.md → ขอบเขตโครงการ](CONTRIBUTING.md#project-scope) เท่านั้น
การตัดสินใจด้านการกำกับดูแลต้องเคารพขอบเขตนี้ คุณสมบัติที่อยู่นอกขอบเขต เช่น
multi-tenancy, AI inference, OTA, B2B และอื่น ๆ ถือเป็นการออกแบบให้อยู่นอกขอบเขตโดยตั้งใจ

### 2. บทบาท

โครงการมี 3 บทบาท ทุกคนสามารถเลื่อนบทบาทได้จากการมีส่วนร่วมอย่างต่อเนื่องและมีคุณภาพ
บทบาทมาพร้อมความรับผิดชอบ ไม่ใช่อภิสิทธิ์

| บทบาท | คือใคร | ทำอะไร |
|---|---|---|
| **ผู้ร่วมพัฒนา (Contributor)** | ทุกคนที่เปิด issue หรือ pull request, ปรับปรุงเอกสาร, ช่วยคัดกรอง หรือรีวิวโค้ด | เสนอการเปลี่ยนแปลง รายงานบั๊ก ช่วยเหลือผู้อื่น ไม่ต้องมีสิทธิ์พิเศษ |
| **ผู้ดูแล (Maintainer)** | ผู้ร่วมพัฒนาที่มีผลงานต่อเนื่องและได้รับสิทธิ์เขียน (write access) | รีวิวและรวมโค้ด (merge), คัดกรอง issue, ออกรุ่น (release), รักษาขอบเขตและ Code of Conduct |
| **ผู้ดูแลหลักของโครงการ (Project Steward)** | เจ้าของโครงการ / ผู้ดูแลหลัก | ตัดสินชี้ขาดเมื่อมีข้อโต้แย้ง, จัดการสมาชิกผู้ดูแล, ดูแลการเปิดเผยช่องโหว่ความปลอดภัยและสัญญาอนุญาต |

ปัจจุบัน **ผู้ดูแลหลักของโครงการ** คือผู้เขียนต้นฉบับและผู้ดูแลลิขสิทธิ์ของแพลตฟอร์มต้นทาง
(ดู [NOTICE](NOTICE)) ผู้ดูแลหลักสามารถมอบหมายความรับผิดชอบใด ๆ ให้ผู้ดูแลคนอื่นได้

### 3. การก้าวขึ้นเป็นผู้ดูแล

ผู้ร่วมพัฒนาอาจได้รับเชิญให้เป็นผู้ดูแลหลังจากแสดงให้เห็นถึง:

- ประวัติการมีส่วนร่วมที่ถูก merge อย่างต่อเนื่องและมีคุณภาพ
- การรีวิวโค้ดที่ดีและวิจารณญาณเรื่องขอบเขตที่เหมาะสม
- การปฏิบัติตาม [Code of Conduct](CODE_OF_CONDUCT.md) และ
  [มาตรฐานการเขียนโค้ด](CONTRIBUTING.md#coding-standards)

ผู้ดูแลคนใดก็ได้สามารถเสนอชื่อผู้ร่วมพัฒนา การเสนอชื่อจะได้รับการอนุมัติด้วย
**ฉันทามติโดยปริยาย (lazy consensus)** ในหมู่ผู้ดูแลปัจจุบัน ผู้ดูแลที่ไม่มีกิจกรรม
เป็นเวลานาน (โดยทั่วไปประมาณ 6 เดือน) อาจถูกย้ายไปสถานะกิตติมศักดิ์ (emeritus) โดย
ผู้ดูแลหลัก และสามารถขอกลับมาทำหน้าที่ได้

### 4. กระบวนการตัดสินใจ

โครงการใช้ **ฉันทามติโดยปริยาย (lazy consensus)** เป็นกระบวนการตัดสินใจหลัก:

1. เสนอการเปลี่ยนแปลงต่อสาธารณะ (issue, discussion หรือ pull request)
2. ผู้ดูแลและผู้ร่วมพัฒนามีช่วงเวลารีวิวที่เหมาะสม (โดยทั่วไปไม่กี่วัน และนานกว่านั้น
   สำหรับการเปลี่ยนแปลงใหญ่หรือที่กระทบความเข้ากันได้)
3. หาก **ไม่มีผู้ดูแลคัดค้าน** ให้ถือว่าข้อเสนอได้รับการยอมรับ และสามารถ merge ได้
   เมื่อ CI ผ่านและมีผู้ดูแลอย่างน้อยหนึ่งคนอนุมัติ
4. หากมี **ความเห็นไม่ตรงกัน** ผู้เสนอและผู้คัดค้านจะหาทางประนีประนอมอย่างเปิดเผย
5. หากหาฉันทามติไม่ได้ ผู้ดูแลคนใดก็ได้สามารถเรียกให้มีการลงคะแนนเสียง

**การลงคะแนน** เมื่อจำเป็นต้องลงคะแนน ผู้ดูแลแต่ละคนมีหนึ่งเสียง ใช้เสียงข้างมากธรรมดา
ของผู้ที่ลงคะแนนภายในช่วงเวลาที่กำหนดเป็นข้อยุติ **ผู้ดูแลหลักของโครงการ** เป็นผู้ชี้ขาด
เมื่อคะแนนเสมอ และในกรณีพิเศษอาจใช้สิทธิ์ยับยั้ง (veto) การตัดสินใจที่จะทำให้โครงการ
ออกนอกขอบเขต ละเมิดสัญญาอนุญาต หรือกระทบต่อความปลอดภัย โดยต้องอธิบายเหตุผลต่อสาธารณะ

**การเปลี่ยนแปลงทั่วไป** (แก้คำผิด เอกสาร แก้บั๊กเล็กน้อย อัปเดต dependency) ต้องการเพียง
การอนุมัติจากผู้ดูแลหนึ่งคนและ CI ผ่านเท่านั้น ไม่ต้องผ่านกระบวนการอื่น

### 5. การเปลี่ยนแปลงการกำกับดูแล สัญญาอนุญาต หรือขอบเขต

สิ่งต่อไปนี้ต้องได้รับการอนุมัติจากผู้ดูแลหลักอย่างชัดเจน และควรหารือกันอย่างเปิดเผย
ก่อน merge:

- การเปลี่ยนแปลงแบบจำลองการกำกับดูแลนี้
- การเปลี่ยนแปลงสัญญาอนุญาตของโครงการ หรือการระบุที่มาใน [NOTICE](NOTICE)
- การเพิ่มหรือลบความสามารถออกจาก
  [ขอบเขตโครงการ](CONTRIBUTING.md#project-scope)
- การนำคุณสมบัติที่ถูกกันออกอย่างชัดเจนกลับมา (multi-tenancy, AI inference, OTA,
  B2B / WebSocket ฯลฯ)

### 6. Code of Conduct และความปลอดภัย

ผู้เข้าร่วมทุกคน รวมถึงผู้ดูแลและผู้ดูแลหลัก ต้องปฏิบัติตาม
[Code of Conduct](CODE_OF_CONDUCT.md) ช่องโหว่ด้านความปลอดภัยให้ดำเนินการตาม
กระบวนการเปิดเผยอย่างประสานงานใน [SECURITY.md](SECURITY.md) โดยผู้ดูแลหลักและผู้ดูแล
จะเป็นผู้จัดการ ไม่ทำผ่าน issue สาธารณะ

### 7. การออกรุ่น (Releases)

ผู้ดูแลออกรุ่นตาม [Semantic Versioning](https://semver.org) และบันทึกไว้ใน
[CHANGELOG](CHANGELOG.md) ผู้ดูแลหลักจะอนุมัติรุ่นที่มีการเปลี่ยนแปลงสัญญาอนุญาต
ขอบเขต หรือพฤติกรรมที่เกี่ยวข้องกับความปลอดภัย
