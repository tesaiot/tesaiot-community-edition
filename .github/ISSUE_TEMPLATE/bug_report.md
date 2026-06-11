---
name: Bug report / รายงานข้อบกพร่อง
about: Report something that is broken in TESAIoT Community Edition / แจ้งสิ่งที่ทำงานผิดพลาด
title: "[Bug] "
labels: bug
assignees: ""
---

<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors

Before filing: please SEARCH existing issues to avoid duplicates.
Do NOT report security vulnerabilities here — see SECURITY.md.
ก่อนแจ้ง: กรุณาค้นหา issue เดิมก่อนเพื่อเลี่ยงการซ้ำ
อย่ารายงานช่องโหว่ด้านความปลอดภัยที่นี่ — ดู SECURITY.md
-->

## Summary / สรุปปัญหา
<!-- One or two sentences. / อธิบายสั้น ๆ หนึ่งถึงสองประโยค -->


## Expected vs. actual / สิ่งที่คาดหวัง เทียบกับ สิ่งที่เกิดขึ้นจริง
- **Expected / คาดหวัง:**
- **Actual / เกิดขึ้นจริง:**

## Steps to reproduce / ขั้นตอนการเกิดซ้ำ
1.
2.
3.

## Environment / สภาพแวดล้อม
- OS / ระบบปฏิบัติการ:
- Docker version (`docker --version`):
- Docker Compose version (`docker compose version`):
- Release tag or commit / เวอร์ชันหรือ commit:
- Affected service(s) / บริการที่เกี่ยวข้อง (api, admin-ui, mqtt-bridge, emqx, apisix, vault, mongodb, timescaledb):

## Logs / บันทึก
<!--
Paste relevant output from `make logs` or `make logs s=<service>`.
REDACT secrets, tokens, certificates and private keys.
วางบันทึกจาก `make logs` หรือ `make logs s=<service>` โดยปกปิดข้อมูลลับ
-->
```
(logs here / วางบันทึกที่นี่)
```

## Additional context / ข้อมูลเพิ่มเติม
<!-- Screenshots, config snippets (no secrets), anything else. / ภาพหน้าจอ หรือข้อมูลอื่น (ห้ามมีข้อมูลลับ) -->
