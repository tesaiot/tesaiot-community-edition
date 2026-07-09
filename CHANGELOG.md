# Changelog

All notable changes to TESAIoT Community Edition are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-07-09

### Added

- **Verified examples suite (`examples/`).** A selective port of the developer-hub
  examples to Community Edition — 12 units across four categories, each adapted to
  CE endpoints/auth and exercised against a live install (telemetry confirmed in
  the `device_telemetry` hypertable; mTLS certificates enrolled through Vault PKI):
  - *Embedded devices* — serverTLS clients in Python (`rpi-servertls`) and
    C/Mongoose (`device-servertls`), an mTLS C client (`device-mtls`), ESP32
    serverTLS firmware (contract-verified on a host simulator), and the shared
    `common-c` Mongoose transport library.
  - *Integrations* — an MQTT telemetry simulator (serverTLS + username/password
    auth added; CE rejects anonymous/plaintext clients) and CE-adapted n8n
    workflows.
  - *Security* — a runnable OPTIGA/PSE84-style secure-element mTLS client
    (on-chip-style EC keygen → CSR → Vault-signed certificate → mTLS publish) and
    a CE-scoped NCSA / EN 303 645 mapping.
  - *Applications* — a React telemetry dashboard (JWT login + CE REST endpoints,
    recharts) and a live MQTT-over-WebSocket streaming dashboard, both charting
    real CE data; Node-RED custom nodes (missing upstream `client.ts` restored so
    the TypeScript builds).
  - Every runnable unit ships a **real-data snapshot** captured from a live
    install, plus per-example CE notes documenting the adaptations: endpoint and
    auth boundaries (API-key = telemetry ingest only, reads are JWT), the mTLS
    requirement to send `username=device_id` + a non-empty password (device API
    key) so the auth webhook can validate the client-certificate CN, and the
    internal-service-account pattern (`mqtt-bridge-*` + `MQTT_BRIDGE_PASSWORD`)
    for fleet-wide MQTT subscriptions.

### Fixed

- **First-run bootstrap CA now carries `keyUsage`, so strict TLS clients can
  verify the HTTPS edge.** `generate-secrets.sh` issued the self-signed bootstrap
  CA without the `keyUsage` extension (and the nginx server leaf without
  `extendedKeyUsage`), so OpenSSL-3-based clients — Python `requests`, Go, Java —
  rejected `https://<host>` with *"CA cert does not include key usage extension"*
  even when given the correct `ca-bundle.pem`. New installs now issue the CA with
  `basicConstraints=critical,CA:TRUE` + `keyUsage=critical,keyCertSign,cRLSign`
  and the server leaf with `keyUsage` + `extendedKeyUsage=serverAuth`.

  **Upgrade note (existing installs):** the fix only affects newly generated
  bootstrap material — an existing install keeps its old certificate until you
  regenerate it:

  ```bash
  rm config/tls/server-cert.pem   # force the bootstrap TLS material to regenerate
  make secrets                    # re-issues the bootstrap CA + server cert
  make init-pki                   # re-appends the Vault chain to ca-bundle.pem
  make restart s=nginx
  ```

  Then redistribute `config/tls/ca-bundle.pem` to any REST/HTTPS clients that pin
  it. MQTT (`8883`/`8884`) is unaffected — EMQX chains to the Vault intermediate
  CA, which always carried proper `keyUsage`.

## [1.2.1] - 2026-07-02

### Security

- **Hardened the log-analytics time-range against SQL injection
  (defense-in-depth).** `get_log_analytics()` built a SQL `INTERVAL` literal by
  string-slicing the caller-supplied `time_range` and interpolating it into four
  queries. It was not reachable (both callers whitelist `time_range`), but the
  function now validates the numeric part to digits and fixes the unit to
  `hours`/`days`, so nothing caller-controlled can reach the SQL string.
- **Stopped logging personal data.** `get_all_organizations()` dumped the full
  authenticated-user object to stdout and `logger.error` on every call (PII in
  logs + error-log pollution); removed.

A security review of v1.2.0 otherwise found no exploitable issues: the setup
wizard is constant-time, fail-closed and one-shot; the API has no Docker socket;
management ports bind to localhost; CORS is fail-closed; and no secrets are
committed.

## [1.2.0] - 2026-07-02

### Added

- **First-run setup wizard.** Install with `make install WIZARD=1` and claim the
  instance from the browser at `/setup`: a four-step wizard (welcome + health →
  administrator → organization → review) gated by a one-time, per-install
  `SETUP_TOKEN` the installer prints — proof of host ownership, never a default
  credential (ETSI EN 303 645 5.1-1/5.1-2; OWASP ASVS 2.5.4). The wizard
  enforces the platform's strong-password policy on the administrator (closing
  the gap where an env-seeded password was never validated), names the single
  organization, and completes atomically with an audit-log entry.
  - **One-shot, server-side.** Once an administrator exists every setup
    endpoint permanently refuses (HTTP 410) — even with the real token — and
    later probes are logged as security events. Completion state lives in
    `system_config` next to the accounts it protects.
  - **Headless installs unchanged.** Plain `make install` still seeds the admin
    from `ADMIN_EMAIL`/`ADMIN_PASSWORD` (first boot only) and auto-skips the
    wizard; existing deployments are backfilled as already-set-up on upgrade.
  - **Host-only recovery.** `make reset-setup` (typed confirmation required)
    removes the admin accounts, rotates the token and reopens the wizard —
    devices, telemetry and certificates are untouched. There is deliberately no
    web-reachable reset.
  - The sign-in page redirects to `/setup` while the instance is unclaimed;
    `scripts/smoke-test.py` now requires explicit credentials instead of
    embedded fallbacks.

## [1.1.8] - 2026-06-21

### Fixed

- **Dashboard device counts no longer exceed the enrolled fleet.** The
  telemetry-derived counts ("active devices (1h)", "devices enrolled (24h)" and
  "active now") counted every distinct `device_id` seen in the time-series
  store, including ids whose device record no longer exists (decommissioned or
  test devices whose telemetry has not yet aged out) — so the dashboard could
  show e.g. *12/3 active* or 14 "enrolled" with only 3 registered devices. All
  three now count only **registered** devices that reported telemetry in the
  window (a shared `_count_registered_devices` intersection), so the figures are
  always a subset of the enrolled fleet.

## [1.1.7] - 2026-06-21

### Fixed

- **Dashboard "Platform Health Score" is accurate.** The detailed system-health
  endpoint built its per-service status only from Docker container stats, which
  the Community Edition API cannot read (it runs without a Docker socket, by
  design). With no containers every service fell back to `unknown`, so the
  dashboard showed **0%**, **0/8 services healthy**, and a misleading **CPU 0% •
  MEM 0%**. It now derives each service's status from the API's own probes
  (MongoDB / Redis / Vault clients, plus the API itself), reports a real
  `platform_health_score`, drops the phantom Prometheus "monitoring" service
  that CE does not ship, and returns CPU/MEM as `null` (the UI hides them) since
  CE has no metrics aggregator.

## [1.1.6] - 2026-06-21

### Fixed

- **Clean application logs.** Several non-fatal conditions that spammed the API
  log are resolved:
  - The time-series telemetry poller ran `MAX(location)` on a JSONB column
    (`function max(jsonb) does not exist`) every few seconds; it now takes one
    value from each `(device_id, time)` group via `array_agg`.
  - The `api_metrics` and `system_logs` observability tables are now created by
    the TimescaleDB init (and on existing installs), so per-request metrics and
    structured logs land instead of logging `relation ... does not exist`.
  - The device-side certificate blueprint was registered twice; the duplicate
    registration (which aborted the certificate-monitoring route setup) is
    removed.
  - PKI role verification at startup now logs an expected, quiet note instead of
    an error when the least-privilege API token cannot list `pki-int/roles`
    (those roles are owned by the bootstrap PKI init).
- **Device certificate status** now reports correctly for issued certificates:
  the status reader reads the stored `expires_at` / `validTo` fields (it
  previously looked only for keys that were never written, so a valid cert
  showed as `unknown`).
- **`ADMIN_BYPASS_RATE_LIMIT` is now actually enforced.** It was documented but
  not implemented; the configured bootstrap admin (`ADMIN_EMAIL`) now bypasses
  both per-IP login throttling and the account-lockout gate, while every other
  account is still rate-limited.

## [1.1.5] - 2026-06-21

### Fixed

- **Clean device-details console.** Viewing a device no longer floods the browser
  console:
  - Verbose `console.log` debug traces (security-tab/algorithm/CSR-detection) are
    stripped from the production bundle; `console.error`/`console.warn` are kept.
  - The Enterprise-only `platform-admin/organizations/<org>/configuration`
    endpoint now has a Community-tier compatibility stub, so it returns sensible
    defaults instead of `404`.
  - The native telemetry WebSocket at `/ws` is now reverse-proxied to the API
    (it was reaching the SPA and failing to upgrade).
  - The **Console** tab's live device-log streaming requires a `/ws/device-logs`
    backend that the Community Edition does not ship; it now shows a clear notice
    instead of opening a WebSocket that always failed. An Enterprise build can
    re-enable it with `VITE_DEVICE_LOG_STREAMING=true`.

### Changed

- Published images now carry an `org.opencontainers.image.description` label so
  the GHCR package pages show what each image is.

## [1.1.4] - 2026-06-21

### Added

- **Open-source governance.** Added [`PRINCIPLES.md`](PRINCIPLES.md) (what is
  free, what is stewarded and why, where revenue goes),
  [`TRADEMARK.md`](TRADEMARK.md) (friendly brand guidelines), and
  [`ADOPTERS.md`](ADOPTERS.md) — all bilingual (EN/TH) — plus a trademark note in
  `NOTICE`.
- **Pre-built container images.** The three TESAIoT-authored images (`api`,
  `admin-ui`, `mqtt-bridge`) are published to `ghcr.io/tesaiot/…` as public,
  multi-arch (linux/amd64 + linux/arm64) images on every release, via a new
  `release-images` GitHub Actions workflow. `make install PREBUILT=1` (or
  `make pull`) pulls them instead of building from source and falls back to a
  source build if they are unavailable; `make install` still builds from source.
  `docker-compose.yml` image references are registry-qualified through
  `TESAIOT_REGISTRY` (default `ghcr.io/tesaiot`), with `BUILD_TAG` still
  selecting the tag.
- **Supply-chain attestations.** Published images are keyless-signed with cosign
  and carry an SBOM and SLSA build provenance; [docs/en/verification.md](docs/en/verification.md)
  §7 shows how to `cosign verify` them.
- **DCO enforced in CI.** A new *DCO sign-off* check requires every pull-request
  commit to carry a `Signed-off-by` trailer; the full DCO text is in the
  [`DCO`](DCO) file.

## [1.1.3] - 2026-06-21

### Fixed

- **mTLS device certificates can be issued again.** Direct Vault PKI issuance
  was hard-coded to the `device-cert` role, whose `key_type=any` Vault permits
  only for `/sign/` (a device-supplied CSR), never `/issue/` (a Vault-generated
  key) — so generating a certificate for an mTLS device failed with *"role key
  type 'any' not allowed for issuing certificates"*. Issuance now uses the
  dedicated EC P-256 `iot-device-ecc` role, and that role allows the device's
  URN identity SAN (`urn:tesa:iot:device:<id>`). A device created with
  `auth_mode: mtls` now receives a working client certificate, connects to the
  EMQX mutual-TLS listener (`:8883`), and its telemetry is stored and readable.
- **Organization API keys now authenticate requests.** Keys minted by the API
  Keys screen were stored and listed but never checked on the request path, so
  they could not actually be used. They are now validated (against the
  `org_api_keys` store) and bind the request to the key's organization as a
  read-only principal. The device telemetry read endpoints
  (`GET /api/v1/devices/<id>/telemetry` and `/telemetry/last`) accept either a
  browser JWT or an `X-API-Key` / `?api_key=` organization key, so telemetry can
  be read straight through the APISIX gateway with a key.
- **Device certificate status endpoint no longer 500s** once a certificate
  exists: it referenced an audit action that was missing from the enum, so every
  status read after issuance raised. The audit action was added.

## [1.1.2] - 2026-06-21

### Fixed

- **Telemetry now persists to TimescaleDB.** The auto-schema writer declared
  `telemetry_generic.device_id` as `UUID` and cast the value with `::uuid`, but
  device ids are arbitrary strings (e.g. `test-sensor-001`), so every
  time-series write failed and rolled back (ingest still returned 200 because
  MongoDB is the primary store). The column is now `TEXT` and the value is
  inserted as-is; the auxiliary `device_telemetry_metadata` table is created on
  demand so its absence can no longer roll back the telemetry write. Telemetry
  is again readable from the time-series tier (dashboard / telemetry API).

## [1.1.1] - 2026-06-21

### Fixed

- A hard refresh of, or a deep link to, the **API Keys** page (and any client
  route that merely starts with `api`) no longer returns a backend 404 — the
  edge `/api/` reverse proxy is now scoped to the API namespace so such routes
  fall through to the single-page app.
- The **Cmd+K global search** palette no longer lists Enterprise-only pages
  that are not part of the Community Edition (Organizations, Platform Admin,
  Analytics, System Health, Activity Logs, 3D Model Store, ACME, etc.).

### Changed

- README now includes a "Screens" tour with a screenshot and highlights for
  each admin-UI page.

## [1.1.0] - 2026-06-21

### Added

- **Organization API keys.** A new **API Keys** screen in the admin UI issues,
  rotates, and revokes organization-scoped API keys for the REST API / gateway,
  backed by new `GET/POST/DELETE /api/v1/organizations/<org>/api-keys` (+`/rotate`,
  `/metrics`) endpoints. Keys are stored only as a SHA-256 hash plus a short
  prefix and shown in full exactly once; they are validated at the API tier
  (APISIX standalone YAML mode has no per-consumer gateway keys).
- **`make smoke`** — an end-to-end smoke test (`scripts/smoke-test.py`, stdlib
  only) that verifies all 11 containers and the login → device → telemetry →
  MQTT → gateway flows. New [docs/en/verification.md](docs/en/verification.md).

### Fixed

- **First-boot admin is now seeded** from `ADMIN_EMAIL`/`ADMIN_USERNAME`/
  `ADMIN_PASSWORD` (mapped through to the organization admin), and login no
  longer rejects single-label hosts such as the default `admin@localhost`.
- **Admin UI builds on Apple Silicon / musl** (npm/`lightningcss` native-module
  resolution); the header now shows the correct **Community** edition badge and
  version.
- **Vault PKI bootstrap** initialises reliably: storage-path permissions, JSON
  parsing of `vault operator init`, stdin forwarding for intermediate-CA signing,
  the agent's server-certificate issuance policy, and persisting the AppRole
  credentials the API needs to start.
- **APISIX** starts and serves correctly (writable runtime config; valid
  `radixtree_sni` SSL router); the health probe no longer depends on `ps`.
- **MongoDB replica set** advertises the in-cluster host so the API can reach
  the primary; database initialization no longer aborts on a non-fatal index
  conflict.
- **TimescaleDB** connection limit raised so the API does not exhaust it on
  start.
- Removed commercial-only surfaces from the Community build (Extensions menu,
  Upgrade call-to-action, DigitalOcean/Prometheus-bound dashboard panels) and
  added compatibility stubs so the UI no longer logs 404s for features the
  edition does not ship.

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
