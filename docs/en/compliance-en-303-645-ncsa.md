<!-- SPDX-License-Identifier: Apache-2.0 -->
# Standards compliance: ETSI EN 303 645 and the NCSA Consumer IoT Cyber Security Guidelines

This document explains how TESAIoT relates to two consumer IoT cybersecurity standards, and it is written for engineers who need to make a real procurement or deployment decision.

The two standards are:

* ETSI EN 303 645 V2.1.1, *Cyber Security for Consumer Internet of Things: Baseline Requirements*. It defines 13 high level provisions plus a set of data protection provisions.
* The NCSA Consumer IoT Cyber Security Guidelines v1.0 (สกมช., Thailand). It defines provisions 6.1 to 6.26 organised into four cumulative levels, and it is built on ETSI EN 303 645 together with ISO/IEC 27400, 27402, 29147 and 30111.

Before the table of results, one point decides how to read everything that follows. Both standards are written for the consumer device and its manufacturer. TESAIoT is the platform that those devices connect to: the API, the MQTT broker, the certificate authority, and the management console. A platform can satisfy the backend half of many provisions directly. The device half (secure boot, an on-device secure element, debug ports, sensor disclosure) belongs to the device firmware. A further group of provisions is operational, meaning they depend on how the system is run over time (applying updates promptly, monitoring, and commissioning an accredited penetration test). For that reason we describe coverage in three layers and we state the gaps with the same precision as the strengths.

## The three layers of coverage

The first layer is the platform itself, the server side, owned by the TESAIoT software. It is implemented in the open source code: the PKI, mutual TLS, fail closed authentication, rate limiting and lockout, secure secret storage, attack surface reduction, input validation, a vulnerability disclosure policy, and supply chain scanning in CI.

The second layer is the reference device, owned by the device firmware and hardware. TESA addresses it with a reference secure device design that uses a hardware secure element (Infineon OPTIGA Trust M) for hardware anchored identity and key storage, and a secure boot capable MCU (PSoC Edge E84, with an Arm Cortex-M33 secure core). The platform already provisions these devices today: it issues a unique per device X.509 identity through Vault PKI and supports the OPTIGA Trust M certificate path. TESA delivers the device side as reference designs and training.

The third layer is operations, owned by whoever runs the system. This covers applying updates on time, monitoring, declaring a support window, and arranging accredited penetration testing. For the Community Edition, which you self host, you own this layer. For the Enterprise Cloud, which TESA operates for you, TESA owns it.

## Result

For the Enterprise Cloud, which TESA fully manages, the service is engineered to meet ETSI EN 303 645 and all four NCSA levels end to end. TESA owns the operational layer (signed and timely updates, monitoring, resilience, periodic accredited penetration testing, and a published support lifecycle) and pairs the managed platform with the TESA reference secure device, so the device side requirements are covered as well.

For the Community Edition, which is self hosted under Apache-2.0, the platform meets about 70 percent of the NCSA Level 1 and Level 2 baseline out of the box at the platform layer. Coverage rises toward full when the Community Edition is paired with the TESA reference secure device (the second layer) and with sound operations (the third layer). The remaining product gaps are listed below and are tracked on the roadmap.

The difference between the two editions is not a weaker codebase. They run the same secure core. The difference is that a managed service can also guarantee the operational layer and ship a certified device, while a self hosted deployment's final posture depends on how the operator runs it.

## What the platform meets out of the box

The claims below were verified against the source code at the v1.0.0 release.

### Level 1, the security baseline

No universal default passwords (provision 6.1.1, ETSI 5.1). Every install generates strong random secrets, and the platform refuses to start in production if any secret is still a placeholder or is weak or short. See `scripts/generate-secrets.sh` and `services/api/api/core/config.py`. Devices receive a unique per device X.509 certificate from Vault PKI, never a shared default.

Authentication and brute force resistance (provisions 6.1.3 to 6.1.5, ETSI 5.1). Passwords are hashed with bcrypt using an environment configurable cost, login is protected by per IP and per account lockout (Redis backed, with an in memory fallback), every HTTP 429 response carries a Retry-After header, and secret comparison is constant time. See `services/api/api/utils/validation.py` and `services/api/api/core/auth.py`.

Vulnerability disclosure (provision 6.2.1, ETSI 5.2). A full coordinated disclosure policy is published in `SECURITY.md`, in both English and Thai.

Published support window and identifiable version (provisions 6.3.6 and 6.3.7). The supported versions table lives in `SECURITY.md`, and the running version is identifiable through `VERSION.txt`, `CHANGELOG.md`, and an `X-Build-Fingerprint` response header.

### Level 2, alignment with international standards

Secure storage of security parameters and no hardcoded secrets (provisions 6.4.1 and 6.4.3, ETSI 5.4). Device private keys live only in HashiCorp Vault, while MongoDB stores references to them. All secrets come from an environment file (set to mode 600) or from Vault. Committed configuration files are templates that carry only placeholders, and the rendered files are git ignored. CI secret scanning enforces this, and the platform refuses to start with a placeholder secret in production.

Unique per device keys (provision 6.4.4). Vault PKI issues the certificates, and the common name is forced on the server side to the device id, so a device cannot request another device's identity.

Communicate securely (provisions 6.5.1 to 6.5.4, ETSI 5.5). The platform uses TLS 1.2 and 1.3 with an AEAD only cipher list (no CBC, no SHA-1). MQTT is served only over TLS. The EMQX mutual TLS listener requires a client certificate, fails if none is presented, and checks the certificate revocation list during the handshake. The mutual TLS gateway marker is non spoofable, is compared in constant time, and fails closed. Device private keys are delivered once, encrypted with a hybrid scheme (RSA-OAEP or ECDH plus AES-256-GCM). The full key lifecycle (issue, renew, revoke) runs in Vault.

Minimize the attack surface (provisions 6.6.1 to 6.6.3, ETSI 5.6). The API and the databases are not published to the host. Management and plaintext ports are bound to 127.0.0.1 only. Docker networks are segmented. The bridge container runs with no new privileges, as read only, and with all capabilities dropped. The API runs under gunicorn in production, with no debug server.

Protect personal data in transit (provision 6.7.1, ETSI 5.8). All device and administrator traffic uses TLS 1.2 or 1.3.

Validate input data (provision 6.9.1, ETSI 5.13). The platform validates schemas, enforces request size limits, validates device ids and telemetry, guards outbound webhook URLs against server side request forgery, and sets security headers on every response.

### Level 3, security by design (aligned with ISO/IEC 27400)

The platform meets the engineering and process provisions that apply to a software product: a secure development pipeline (CI runs shellcheck, ruff, type checking and build, compose validation, and dependency, secret and image scanning), maintained dependencies (CI fails on HIGH or CRITICAL findings), hardening before release, clear security communication through `CHANGELOG.md` and `SECURITY.md`, and a defined vulnerability handling process. Two items are partial: the software bill of materials is generated for the admin UI image but not yet for every image, and vulnerability assessment is currently automated only.

## Gaps in the Community Edition, tracked on the roadmap

We state these plainly so that an engineer can plan around them.

1. Privacy and consent interface (provisions 6.10.1 to 6.10.4, ETSI clause 6). The platform does not ship a consent capture, privacy policy, or telemetry disclosure interface. A regulated deployment must add these. Self hosting does help here, because all telemetry stays on your own infrastructure.
2. Erasure beyond accounts (provision 6.8.1, ETSI 5.11). User account deletion exists and removes data from both MongoDB and Vault. Automated erasure or anonymisation of telemetry records, and a data export feature, do not yet exist.
3. Cryptographically signed updates (provision 6.3.5, ETSI 5.7). Images are pinned by version tag and scanned in CI, but they are not yet pinned by SHA digest or signed (for example with cosign). Secure boot and software integrity (ETSI 5.7) are delivered at the device layer through PSoC Edge secure boot.
4. A formal threat model document (provision 6.11). The threat reasoning is present in the code and configuration, but there is not yet a standalone STRIDE document.
5. Accredited black box penetration testing (NCSA Level 4, provisions 6.19 to 6.26). This is not included in the open source distribution. It is available through the TESA certification path or an Enterprise engagement.
6. Operational provisions (provisions 6.3.1 to 6.3.4: timely updates, support, monitoring). The self host operator owns these in the Community Edition. TESA owns them in the Enterprise Cloud.
7. Device only provisions (tamper resistant secure element 6.4.2 and ETSI 5.4, on device debug port disablement 6.6.3, sensor disclosure 6.7.2, and secure boot ETSI 5.7). These are satisfied by the TESA reference secure device, the second layer, not by the platform on its own.

## A note on ETSI EN 303 645 items that NCSA has not adopted

The NCSA v1.0 Appendix C lists a number of ETSI EN 303 645 items that it has not yet adopted. Among them are three complete objectives that have no NCSA equivalent at all, and which TESAIoT therefore tracks separately: 5.7 (ensure software integrity, including secure boot), 5.9 (resilience to outages), and 5.10 (examine telemetry for anomalies). The TESA reference device covers 5.7 through PSoC Edge secure boot and 5.4 through the OPTIGA Trust M secure element. Resilience (5.9) and telemetry anomaly examination (5.10) are part of the managed Enterprise Cloud operations. So "meets NCSA" and "meets the full ETSI EN 303 645" are different statements, and this document keeps them distinct.

---

This mapping reflects the codebase at the v1.0.0 release. Provision numbers follow the NCSA v1.0 guideline, and the ETSI references are to EN 303 645 V2.1.1 (2020-06). Corrections are welcome through the vulnerability disclosure and contribution processes.
