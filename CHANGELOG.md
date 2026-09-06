# Changelog

All notable changes to TESAIoT Community Edition are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.3] - 2026-09-06

### Fixed

- **The job that proves the admin UI still builds had not built anything for
  months.** `Build admin UI` runs `npx eslint src` before `tsc` and `vite build`,
  and eslint exited 1 on 900 errors — 899 of them `no-explicit-any` — so the two
  steps that actually verify the build never ran. A genuinely broken UI and a UI
  with 899 untyped values looked identical from CI.
  `no-explicit-any` is now a warning, and the count is ratcheted: CI reads
  `services/admin-ui/.eslint-any-baseline` (899) and fails if the number grows.
  New code cannot add one, the existing ones can be typed a file at a time, and
  the build is verified again in the meantime. Removing all 899 is a typing
  effort with its own work package, not a cleanup.
  The one error that was not `no-explicit-any` is fixed rather than downgraded:
  `withErrorBoundary<P extends {}>` in `error-boundary.tsx` now constrains to
  `object`, because `{}` admits `0` and `""`.

## [1.3.2] - 2026-09-06

### Fixed

- **Two model helpers called a pydantic 2 API while the project pins pydantic 1,
  so they raised `AttributeError` on a live path.**
  `CSRWorkflowStatusModel.to_mongo_dict()` and `EnhancedDeviceLog.to_mongo_dict()`
  called `model_dump(by_alias=True, exclude_none=True)`, which exists only in
  pydantic 2; `services/api/requirements.txt` pins 1.10.13. Every CSR workflow
  status and every enhanced device log failed at the moment of writing the
  document — `csr_workflow_service.py` and `enhanced_device_log_service.py` both
  go through those helpers before inserting, and the EMQX events webhook reaches
  the first of them when a device connects. The blueprint is guarded, so the API
  still booted and the feature simply stopped working.
  Both files state their target major in a comment a few lines above the fault
  (`# Pydantic v1 compatibility - use allow_population_by_field_name instead of
  v2's populate_by_name`), so this was a slip against the file's own stated
  intent rather than a deliberate upgrade. Both now call
  `dict(by_alias=True, exclude_none=True)`, the pydantic 1 spelling of the same
  operation. Verified rather than assumed: both models rendered through
  `to_mongo_dict()` under pydantic 1.10.13 with `.dict()` and under 2.9.2 with
  `model_dump()` produce identical documents, including a case exercising nested
  models, `None` values inside nested structures and an undeclared extra field.
  Neither call site passes `mode=`, so no pydantic 2 behaviour is given up.
  Migrating the service to pydantic 2 remains the right long-term answer — 1.10
  is end of life — but it is separate work: `Field(regex=)` is removed in v2, and
  the eight `allow_population_by_field_name` configs stop populating aliases
  there, which on these models means `_id` silently becomes a random UUID.

- **A form hook ran conditionally, which is the "rendered fewer hooks than
  expected" crash.** `useFormField` called `useFormContext()` after an early
  return, so the hook ran on some renders and not others. The call moved above
  the guard, and the guard widened to cover a null form context.

- **A block of JSX wrapped three sibling elements in one expression**, which is a
  parse error. `tsc` stops at parse errors before any semantic checking, so that
  single line was hiding 721 type errors across 136 files. Those remain — the
  build does not type-check them today — but they are now visible to anyone who
  turns type-checking on.

- **Two CI jobs failed before they ran anything.** `shellcheck` had been red
  since v1.3.0 on an unused variable in `reset-setup.sh`, and both Trivy jobs
  died resolving an action tag upstream had removed, so nothing in this
  repository had ever actually been scanned. A genuinely broken build looked
  exactly like the status quo.

### Security

- **Removed `authlib`.** Trivy's first completed dependency scan reported
  authlib 1.3.2 / CVE-2026-27962 as CRITICAL — an authentication bypass via the
  JWK header. Nothing imported it: one grep hit across the repository, and that
  hit was the requirements line itself. It came along when CE was split out of
  the full platform. JWT handling here is PyJWT.

- **The two dashboard examples no longer run nginx as root.** Both inherited
  `nginx:alpine` and never dropped privileges. An example is what people copy
  from, so shipping one that runs as root in a distribution documenting
  ETSI EN 303 645 teaches the opposite of the point. They now use the treatment
  the admin UI image already had, listening on 8080 because an unprivileged
  process cannot bind below 1024; the published ports are unchanged.

### Added

- **Unit tests for model serialisation** (`services/api/tests/unit/test_model_serialisation.py`)
  — six tests that import the real models and exercise `to_mongo_dict()`,
  including the nested and `exclude_none` shapes. Proven in both directions: with
  the fix reverted they fail, with it applied they pass.

- **A guard against calling the wrong pydantic major**
  (`scripts/check-pydantic-major.sh`, wired into the lint job). It reads the pin
  out of `requirements.txt` and rejects the spellings that pin forbids, in both
  directions, so a future migration flips the check by editing one line. Neither
  `ruff` nor `compileall` could see the fault it guards against: `model_dump()`
  is a valid attribute access to both, and CI installed neither pydantic nor the
  models. The unit-test job now installs pydantic by reading the same pin rather
  than repeating the version number.

- **`docs/en/dependency-upgrades-2026-08.md`** records the triage of the
  remaining 82 dependency findings — which can be done safely, which need their
  own branch and test cycle, and which cannot be verified on the build host at
  all.

## [1.3.1] - 2026-08-06

### Fixed

- **Telemetry timestamps now say which timezone they are in.** MongoDB stores
  BSON dates in UTC and pymongo hands them back with no `tzinfo`; a bare
  `.isoformat()` on one of those produces a string with no offset, and every
  browser reads that as *local* time. With the compose default
  `TZ=Asia/Bangkok`, the dashboard telemetry chart therefore rendered seven
  hours behind the instant that was actually recorded. The new
  `api/utils/timefmt.py` refuses to guess between the two kinds of naive
  datetime — `utcnow()` produces naive UTC, `now()` produces naive local, and
  they need *opposite* corrections — so the caller states which it holds with
  `iso_from_utc_naive()` or `iso_from_local_naive()`. Fixed on the paths that
  reach a browser: `GET /api/v1/devices/<id>/telemetry` (what the admin UI
  chart reads), `GET /api/v1/telemetry/unified/<id>` (what the shipped React
  dashboard example reads), the device-details telemetry summary, the shared
  `fix_telemetry_data()`/`fix_certificate_data()` shapers, and every payload on
  the `/ws` telemetry socket. Deliberately unchanged: the TimescaleDB read path
  (its `time` columns are `TIMESTAMPTZ`, so psycopg2 already returns an aware
  datetime), the call sites that append their own `'Z'` (adding an offset there
  would emit `...+00:00Z`, which is `Invalid Date`), and internal bookkeeping
  timestamps that are never serialised.
- **Certificates no longer all report "0 days until expiry".** Once
  `valid_to` carried a UTC offset, the `days_until_expiry` arithmetic beside it
  was still comparing against a naive `datetime.now()`. Subtracting a naive
  datetime from an aware one raises `TypeError`, the surrounding `except`
  swallowed it, and every certificate came back with `0` — an expiry warning
  that fires constantly is one nobody reads. Both sides are now aware.
- **OPTIGA™ Trust M devices are matched by UID without regard to hex letter
  case.** The device reports its UID uppercase in the MQTT client id
  (`CD16334D…`) while the platform stores it lowercase when the device bundle
  is generated (`cd16334d…`). The UID is hex, so the case carries no meaning,
  but an exact match rejected devices whose record was sitting right there —
  logged, misleadingly, as *"Trust M device not pre-registered"*. Both halves
  are fixed: the device lookup in `mqtt_auth_service`, and the ACL lookup in
  `emqx_auth` — where a miss was worse than a refused connection, because the
  device connected successfully and then silently carried no telemetry. The
  lookup uses a small `$in` set rather than a case-insensitive regex so the
  `trustm_uid` index stays usable.

### Added

- **Trust anchors that are not part of the Vault PKI now survive certificate
  renewal.** `vault-ca-bundle.pem` is rewritten from the Vault bundle on every
  renewal, so a CA appended to it by hand — an organisation's own device CA, or
  the Infineon factory CA needed to accept an OPTIGA™ Trust M secure element —
  disappeared the next time the server certificate rotated. Devices that had
  worked for weeks began failing with `unknown_ca` while the broker still
  reported healthy. Drop the certificate in
  `/opt/emqx/etc/certs/trust-anchors.d/` instead and `split-emqx-bundle.sh`
  re-appends it on every run. The directory is created automatically; files
  that do not parse as a PEM certificate are skipped with a warning rather than
  appended, since a truncated anchor would corrupt the bundle and stop every
  TLS listener. Documented in `docs/{en,th}/security-tls-mtls.md`.
- **`healthcheck.sh` now reports an `emqx-tls` row.** `emqx ctl status` answers
  "is the broker alive?", which stays green while every TLS handshake is being
  refused. The new check covers the two things that actually have to hold: that
  the broker can *read* its key, certificate and CA bundle (asked from its own
  side — `docker exec` runs as the image's uid, so a root-owned key that EMQX
  cannot open is caught), and that the `ssl:mtls` and `ssl:servertls` listeners
  are genuinely running.
- **Python unit tests and a CI job to run them.** `services/api/tests/` with
  coverage of the timestamp helpers, the two response shapers that use them,
  and the Trust M UID matching. They need no running stack. CI runs the suite
  twice — once under `TZ=Asia/Bangkok` and once under `TZ=UTC`; if the two runs
  ever disagree, a timezone assumption has leaked back into the code.

### Changed

- **Capabilities that belong to Enterprise Cloud are now labelled as such.**
  The admin UI told the operator to "trigger a Protected Update job" to rotate
  an OPTIGA™ Trust M device onto platform-issued credentials, but Protected
  Update is not shipped in the Community Edition (see `PRINCIPLES.md` and
  `examples/security/ncsa/`) — there is no such job in this build. Instructions
  for a button that is not there read as a broken install long before they read
  as an edition boundary. Those screens now carry an *Enterprise only* marker
  and point at the CSR workflow, which is the supported way to do the same
  rotation here. The inert `PROTECTED_UPDATE_*` settings and the
  `mqtt-bridge-protected-update` service identity are annotated rather than
  removed, so the configuration surface still matches Enterprise Cloud for
  anyone migrating between the two.

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
