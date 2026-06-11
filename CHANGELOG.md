# Changelog

All notable changes to TESAIoT Community Edition are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-12

Initial public release of **TESAIoT Community Edition** — a free, self-hostable,
single-organization IoT platform, secure by design and released under
Apache-2.0. Extracted and relicensed from the TESAIoT Secure IoT Platform, and
ready to run in minutes with Docker Compose.

### Features

1. **User Management** — local user accounts, roles, and authentication for a
   single organization.
2. **Device / Identity Management** — register, list, and manage IoT device
   identities and their lifecycle.
3. **serverTLS and mTLS authentication modes** — both server-side TLS and
   mutual-TLS device authentication.
4. **Certificate life-cycle management** — issue, renew, and revoke
   device/server certificates via HashiCorp Vault PKI.
5. **APISIX API gateway** — unified edge gateway routing and securing platform
   APIs.
6. **EMQX MQTT broker** — MQTT ingestion broker for device telemetry and control.
7. **MongoDB & TimescaleDB** — MongoDB for document/metadata storage and
   TimescaleDB for time-series telemetry.
8. **IoT telemetry dashboard** — telemetry visualization embedded in the device
   details view.

### Security by design

- **Device identity is gateway-verified.** Device endpoints require either
  nginx-terminated mTLS (proven by a non-guessable `X-MTLS-Gateway` marker the
  API checks in constant time) or a device API key; the claimed device id is
  bound to the authenticated identity. No `X-*` header is trusted on its own.
- **PKI cannot be used to spoof identities** — Vault issues certificates with
  the common name forced server-side to the device id; private keys live only in
  Vault and are delivered once, encrypted.
- **Fail-closed everywhere it matters** — boot refuses to start on missing/
  placeholder secrets; the EMQX auth/ACL/events webhooks require a constant-time
  bearer; CORS is an explicit env-driven allowlist (never `*` with credentials);
  the API runs under gunicorn (not the Flask dev server).
- **Least privilege** — the MQTT telemetry bridge runs as a dedicated `service`
  role (telemetry-ingest + device-update only), not an admin account; the Vault
  app token is scoped to the specific PKI roles it needs.
- **Abuse resistance** — Redis-backed login rate limiting with account lockout, a
  `Retry-After` header on every 429, trusted-proxy `X-Forwarded-For` handling,
  and an SSRF guard on admin-configured webhook URLs.
- **Hardened transport & secrets** — TLS 1.2/1.3 with an explicit AEAD-only
  cipher list; secret-bearing config files are rendered from versioned `*.tpl`
  templates and git-ignored; current, audited dependencies.
- **Operations** — one-command `make install`; HashiCorp Vault can self-unseal
  on restart (opt-out) with `make unseal` for manual recovery; backups capture
  the Vault and EMQX data volumes; CI lints, type-checks, builds and runs
  dependency/secret scans on every change.

### Notes

- Multi-tenancy is collapsed to a single default organization.
- Excluded from this distribution: AI inference, Flowise, OTA / firmware update,
  WebSocket B2B features, third-party services (BENTO IDE, Developer Hub,
  summit sites), analytics module, and the Grafana/Prometheus monitoring stack.

[1.0.0]: https://github.com/tesaiot/tesaiot-community-edition/releases/tag/v1.0.0
