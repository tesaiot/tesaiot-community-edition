<!-- SPDX-License-Identifier: Apache-2.0 -->
# Standards compliance — ETSI EN 303 645 & NCSA Consumer IoT Cyber Security Guidelines

This document maps **TESAIoT** to two consumer-IoT cybersecurity standards:

- **ETSI EN 303 645 V2.1.1** — *Cyber Security for Consumer Internet of Things: Baseline Requirements* (13 high-level provisions + data-protection provisions).
- **NCSA Consumer IoT Cyber Security Guidelines v1.0** (สกมช., Thailand) — provisions **6.1–6.26** organised in **4 cumulative levels**, built on ETSI EN 303 645 and ISO/IEC 27400/27402/29147/30111.

> **Read this honestly.** These standards are written for the **consumer device** and its **manufacturer**. TESAIoT is the **platform / server side** that devices connect to (API, MQTT broker, PKI, dashboard). A platform can directly satisfy the *backend half* of many provisions; the *device half* (secure boot, on-device secure element, debug ports, sensor disclosure) belongs to the device, and several provisions are *operational* (applying updates on time, monitoring, accredited penetration testing). We therefore describe coverage in **three layers**, and we publish the gaps as openly as the strengths.

## Three layers of coverage

| Layer | Who owns it | In TESAIoT |
|------|-------------|------------|
| **1. Platform (server side)** | the TESAIoT software | Implemented in the open-source code: PKI, mTLS, fail-closed authentication, rate-limiting, secure storage, attack-surface minimisation, input validation, vulnerability disclosure, supply-chain scanning. |
| **2. Reference device** | the device firmware/hardware | Covered by **TESA's reference secure-device architecture**: a **hardware secure element / HSM (Infineon OPTIGA™ Trust M)** for hardware-anchored identity and key storage, and a **secure-boot–capable MCU (PSoC™ Edge E84, Arm Cortex-M33 secure core)**. The platform already **provisions** these devices (per-device X.509 via Vault PKI, OPTIGA Trust M certificate path). TESA delivers the device side as reference designs and training. |
| **3. Operations** | the operator | Applying updates promptly, monitoring, defining a support window, accredited penetration testing. For **Community Edition (self-host) the operator owns this layer**; for **Enterprise Cloud, TESA owns it**. |

## Headline result

| Edition | ETSI EN 303 645 / NCSA coverage |
|--------|---------------------------------|
| **TESAIoT Enterprise Cloud** (fully managed by TESA) | **Targets 100% across NCSA Levels 1–4.** TESA owns the operational layer (signed, timely updates; telemetry/anomaly monitoring; resilience; periodic accredited penetration testing; published support lifecycle) and pairs the managed platform with the TESA reference secure device, so the device-side provisions are satisfied too. |
| **TESAIoT Community Edition** (self-host, Apache-2.0) | **≈ 70% of the NCSA Level 1–2 / ETSI EN 303 645 baseline is met out-of-the-box at the platform layer.** Coverage rises toward full when CE is paired with TESA's reference secure device (layer 2) and sound operator practices (layer 3). The residual product gaps below are on the roadmap. |

The difference is **not** a weaker codebase — Enterprise Cloud and Community Edition run the **same secure core**. The difference is that a managed service can *also* guarantee the operational layer and ship a certified device, whereas a self-hoster's final posture depends on how they operate it.

## What the platform meets out-of-the-box (verified, with evidence)

**Level 1 — Security baseline**

- **No universal default passwords (6.1.1 / EN 5.1)** — every install generates strong random secrets; boot is **fail-closed** and refuses any `CHANGEME`/weak/short secret in production (`scripts/generate-secrets.sh`, `services/api/api/core/config.py`). Devices get **unique per-device X.509 certificates** (Vault PKI), never a shared default.
- **Authentication & brute-force resistance (6.1.3–6.1.5 / EN 5.1)** — bcrypt password hashing (env-configurable rounds), per-IP **and** per-account lockout (Redis-backed, in-memory fallback), and a `Retry-After` header on every `429`; constant-time secret comparison (`services/api/api/utils/validation.py`, `core/auth.py`).
- **Vulnerability disclosure (6.2.1 / EN 5.2)** — a full coordinated-disclosure policy (`SECURITY.md`, EN + TH).
- **Published support window & identifiable version (6.3.6 / 6.3.7)** — `SECURITY.md` supported-versions table; `VERSION.txt`, `CHANGELOG.md`, and a runtime `X-Build-Fingerprint` header.

**Level 2 — International standards**

- **Securely store sensitive parameters / no hardcoded secrets (6.4.1, 6.4.3 / EN 5.4)** — device private keys live **only** in HashiCorp Vault (MongoDB stores references); all secrets come from `.env` (chmod 600) or Vault; committed configs are `*.tpl` templates with `CHANGEME` placeholders only; CI secret-scanning enforces it.
- **Unique per-device keys (6.4.4)** — Vault PKI, with the certificate common name **forced server-side** to the device id so a device cannot request another device's identity.
- **Communicate securely (6.5.1–6.5.4 / EN 5.5)** — TLS 1.2/1.3 with an **AEAD-only** cipher list (no CBC/SHA-1); MQTT only over TLS; EMQX mTLS with `verify_peer` + `fail_if_no_peer_cert` + **CRL revocation checked at the TLS handshake**; a non-spoofable mTLS gateway-marker (`hmac.compare_digest`, fail-closed); one-time **hybrid-encrypted** private-key delivery (RSA-OAEP/ECDH + AES-256-GCM); full Vault key lifecycle (issue/renew/revoke).
- **Minimize attack surface (6.6.1–6.6.3 / EN 5.6)** — the API and database are **not published** to the host; management/plaintext ports bound to `127.0.0.1` only; segmented Docker networks; `no-new-privileges`, read-only and `cap_drop: ALL` on the bridge; gunicorn in production (no debug server).
- **Protect personal data in transit (6.7.1 / EN 5.8)** — all device and admin traffic over TLS 1.2/1.3.
- **Validate input data (6.9.1 / EN 5.13)** — schema validation, request-size limits, device-id and telemetry validation, an **SSRF guard** on outbound webhook URLs, and security headers on every response.

**Level 3 — Security-by-Design (per ISO/IEC 27400)**

- **Met:** secure engineering / SDLC (CI runs shellcheck, ruff, type-check + build, compose validation, **dependency, secret and image scanning**); maintained dependencies (CI fails on HIGH/CRITICAL); hardening before release; clear security communication (`CHANGELOG.md`, `SECURITY.md`); vulnerability handling.
- **Partial:** SBOM is generated for the admin-UI image (CycloneDX) but not yet for every image; vulnerability assessment is automated-only.

## Honest gaps (Community Edition, tracked on the roadmap)

We would rather you trust us because we are precise than because we rounded up.

1. **Privacy / consent UX (6.10.1–6.10.4 / EN §6)** — the platform does not ship a consent-capture, privacy-policy or telemetry-disclosure UI. A regulated deployment must add these. *Mitigation in CE: self-hosting keeps all telemetry on your own infrastructure.*
2. **Right-to-erasure beyond accounts (6.8.1 / EN 5.11)** — user-account deletion (MongoDB + Vault) exists; automated telemetry-record erasure/anonymisation and data export do not yet.
3. **Cryptographically signed updates (6.3.5 / EN 5.7)** — images are version-tag-pinned and CI-scanned, but not yet SHA-digest-pinned or signed (e.g. cosign). **Secure boot / software integrity (EN 5.7)** is delivered at the **device** layer (PSoC Edge secure boot).
4. **Formal threat-model document (6.11)** — threat reasoning is embedded in the code and configs but not yet a standalone STRIDE document.
5. **Accredited black-box penetration test (NCSA Level 4, 6.19–6.26)** — not included in the open-source distribution; available through the TESA certification path / Enterprise engagement.
6. **Operational provisions (6.3.1–6.3.4 timely updates, support, monitoring)** — owned by the self-host operator in CE; owned by TESA in Enterprise Cloud.
7. **Device-only provisions** (tamper-resistant secure element 6.4.2/EN 5.4, on-device debug-port disablement 6.6.3, sensor-disclosure 6.7.2, secure boot EN 5.7) — satisfied by **TESA's reference secure device** (layer 2), not by the platform alone.

## Note on ETSI EN 303 645 provisions NCSA did not adopt

NCSA v1.0's Appendix C lists a number of EN 303 645 items it has not yet adopted. Among them are **three whole top-level objectives** that have no NCSA equivalent at all and that TESAIoT therefore tracks separately: **5.7 ensure software integrity / secure boot**, **5.9 resilience to outages**, and **5.10 examine telemetry for anomalies**. TESA's reference device covers **5.7** (PSoC Edge secure boot) and **5.4** (OPTIGA Trust M secure element); resilience (5.9) and telemetry-anomaly examination (5.10) are part of the managed Enterprise Cloud operations. So "meets NCSA" and "meets full EN 303 645" are tracked distinctly and honestly here.

---

*This mapping reflects the codebase at the v1.0.0 release. Provision numbering follows the NCSA v1.0 guideline; the ETSI references are to EN 303 645 V2.1.1 (2020-06). Corrections welcome via the vulnerability-disclosure and contribution processes.*
