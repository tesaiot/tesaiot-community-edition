<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# TESAIoT Community Edition — Examples

Working examples for connecting devices and applications to a **Community Edition**
install. These are a **selective port** of the cloud
[developer-hub examples](https://github.com/tesaiot/developer-hub/tree/main/examples):
the cloud examples target features that CE ships (serverTLS/mTLS devices, MQTT, REST
telemetry) **and** features CE deliberately excludes (analytics/AI, OTA, SSO, WSS/B2B,
Grafana, MQTT-over-QUIC). Only the examples that map to a real CE capability are ported
here, and each is adapted to CE endpoints and auth.

> **Acceptance bar:** an example is only published here once it has been demonstrated
> working against a **running CE instance** (real connect + telemetry landing in
> TimescaleDB / Device Details). Analysis-only candidates stay in the plan below until
> they clear that bar.

## The 8 capabilities an example may use

User management · Device/identity management · serverTLS & mTLS · Vault PKI certificate
lifecycle · APISIX API gateway (key-auth) · EMQX MQTT broker · MongoDB + TimescaleDB ·
IoT telemetry dashboard. Anything outside this set (analytics, AI inference, OTA, SSO,
WSS/B2B, Grafana/Prometheus, multi-tenancy) is **not** part of CE.

## Available now

| Example | Path | CE capabilities | Status |
|---|---|---|---|
| serverTLS device client (Python) | [`embedded-devices/rpi-servertls`](embedded-devices/rpi-servertls) | #3 #5 #6 #7 #8 | ✅ **verified end-to-end** (MQTT), REST functional |

## Porting status of all 24 developer-hub units

Full analysis, per-unit required changes, and the phased plan live in
[`TESAIoT_PLAN/examples-ce-compatibility-triage.md`](../TESAIoT_PLAN/examples-ce-compatibility-triage.md).
Runtime evidence lives in
[`TESAIoT_PLAN/examples-vv-evidence.md`](../TESAIoT_PLAN/examples-vv-evidence.md).

### Ported / planned (13 map to CE with adaptation)

| Unit | Maps to | Effort | Notes |
|---|---|---|---|
| `emb-rpi-servertls` | serverTLS MQTT + REST | low | **Published & verified** (this repo) |
| `emb-device-servertls` (C) | serverTLS MQTT + REST | low | fix HTTPS CA-trust (`ca_chain=NULL`), repoint host |
| `emb-esp32-servertls` | serverTLS MQTT | low | CE CA into `ca_cert.h`; needs hardware |
| `emb-device-mtls` (C) | mTLS | medium | fix CA-trust; EMQX `8883` not host-mapped |
| `shared-common` (C lib) | dependency | low | trim cloud/QUIC refs; used by the C examples |
| `int-edge-ai-device-simulator` | MQTT telemetry | medium | add TLS + username/password (currently plain 1883) |
| `emb-python-cli` | REST | high | add JWT login for reads; drop `/external`, `/ws/telemetry` |
| `app-react-dashboard` | REST telemetry | medium | rewrite endpoints; remove committed API key |
| `app-live-streaming-dashboard` | MQTT-over-WS | medium | broker → `ws://localhost:8083`; drop `tesa_mqtt_` token auth |
| `app-nodered-integration` | REST | high | restore missing `client.ts`; JWT reads; remove WSS node |
| `int-n8n-automation` | REST | medium | re-architect anomaly-webhook alert to schedule-poll |
| `sec-ncsa` | docs | low | strip excluded-feature sections; fix symlinks |
| `sec-pse84-client` (HW) | mTLS | medium | HW; menu-3 cert-renewal gated on CE |

`sec-rpi-client` (HW secure-element) is **copy-with-caveat**: CSR-over-MQTT enrollment
and Protected Update have no server-side answer in stock CE.

### Not ported (10 depend on an excluded feature — do **not** copy)

`analytics-api`, `int-ai-service-template` (AI/analytics) · `app-grafana-dashboard`
(Grafana) · `emb-c_ota_client` (OTA) · `emb-mqtt-quic-advanced`, `emb-mqtt-quic-python`,
`int-mqtt-quic-c` (MQTT-over-QUIC) · `app-wss-mqtt-streaming`, `int-wss-live-streaming`
(WSS/B2B + org MQTT tokens) · `sec-identity-sso` (Keycloak OIDC).

## Shared adaptation rules (when porting the rest)

1. Endpoints → `localhost` (API `https://localhost`, MQTT serverTLS `:8884`, mTLS `:8883`,
   WS `:8083`).
2. Drop the `/api/v1/external` prefix — CE has no `external` blueprint.
3. Auth boundary: `X-API-KEY` authorizes **telemetry ingest only**; device/dashboard
   reads are JWT-only (`POST /api/v1/auth/login`).
4. Use the CE Vault-PKI CA (`config/tls/ca-bundle.pem`); never ship `verify=False` /
   `CERT_NONE` / `ca_chain=NULL` / `rejectUnauthorized:false`.
5. Remove excluded-feature code (analytics/AI, OTA, WSS/`tesa_mqtt_` tokens, QUIC,
   Keycloak, Grafana) and all `organization_id` (CE is single-org).
6. MQTT topic `device/<id>/telemetry`; strip committed secrets; fix stale port/auth docs.
