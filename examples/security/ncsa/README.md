<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Security & NCSA / EN 303 645 mapping (Community Edition)

How the Community Edition examples map onto the baseline consumer-IoT security
provisions of **ETSI EN 303 645** and the NCSA levels CE actually supports.

> Community Edition ships the **transport-security and certificate-lifecycle** half of
> the security story. Levels/controls that depend on excluded features — Keycloak SSO
> (OIDC), HSM key provisioning, SBOM generation, Zero-Trust gateway, protected-update
> (OTA), quantum-ready crypto — are **out of scope for CE** and are intentionally not
> represented here. See the platform docs for the full-suite capabilities.

## What CE covers

| Level | Control | CE capability | Example |
|---|---|---|---|
| 1 | No default passwords | First-run setup wizard; no seeded credentials | platform (`make install WIZARD=1`) |
| 1 | Secure transport (server TLS) | EMQX serverTLS `:8884`, HTTPS via nginx/APISIX | [`../../embedded-devices/device-servertls`](../../embedded-devices/device-servertls), [`rpi-servertls`](../../embedded-devices/rpi-servertls) |
| 2 | Mutual authentication (mTLS) | EMQX mTLS `:8883`, client cert required | [`../../embedded-devices/device-mtls`](../../embedded-devices/device-mtls) |
| 2 | Per-device identity & credentials | Device registry + per-device MQTT creds / API keys | Device Management |
| 2 | Certificate life-cycle | Two-tier Vault PKI (root → intermediate), issue/renew/revoke | `POST /api/v1/certificates/devices/{id}/certificate/sign-csr` |
| 2 | Communicate securely / validate CA | Private CA chain (`config/tls/ca-bundle.pem`); clients verify the broker/edge | every device example |

## EN 303 645 provisions demonstrated by the examples

- **Provision 5.1 (no universal default passwords):** setup wizard + per-device
  credentials — no shared secrets.
- **Provision 5.5 (secure communication):** all device examples use TLS with CA
  verification; none disable certificate checking.
- **Provision 5.4 / 5.8 (secure credential storage & data in transit):** mTLS client
  certificates issued from Vault PKI; keys generated on the device (or secure element).

## Not in Community Edition (documented, not shipped)

Keycloak SSO/OIDC, HSM provisioning, SBOM (CycloneDX) generation, Zero-Trust gateway,
protected-update / OTA, and quantum-ready crypto are excluded from CE by design. The
upstream `security/` tree in the developer hub contains those references for the
full platform; they have no CE endpoint to run against.
