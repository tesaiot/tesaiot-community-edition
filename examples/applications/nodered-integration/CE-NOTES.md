# Community Edition notes

Custom Node-RED nodes for TESAIoT (`tesaiot-api-gateway`, `-device-data`, `-device-lists`,
`-device-profile`, `-api-usage`), adapted to a self-hosted Community Edition install.

## CE adaptations applied
- Node base URLs repointed from `admin.tesaiot.com/api/v1/external` → `https://localhost/api/v1`
  (config nodes, node HTML placeholders). CE has no `external` blueprint.
- **Restored `src/lib/client.ts`** (it was missing upstream, so `tsc` could not build). It is
  a minimal `fetch`-based client exposing `get(path, params?)`, supporting both an API key
  (`X-API-KEY`) and a bearer `token` for CE's JWT-gated read endpoints.
- Removed the WSS/real-time streaming node target and `organization_id` (excluded/single-org
  on CE) where present in config.

## Remaining CE wiring
- **Auth boundary:** `device-data` (telemetry) works with an API key; `device-lists` /
  `device-profile` / dashboard reads are **JWT-only** — set the `token` on the config node
  (from `POST /api/v1/auth/login`).
- The upstream `tesaiot-telemetry-stream` WSS node is not supported on CE (B2B/WebSocket is
  excluded) — use the MQTT-over-WS listener (`ws://localhost:8083/mqtt`) or the REST nodes.

## Build & run
```bash
npm install
npm run build       # tsc + asset copy (client.ts restored so the TS compiles)
npm start           # launches Node-RED with these nodes registered
```

> Status: source- and endpoint-adapted for CE with the missing client restored. Full flow
> verification requires a running Node-RED instance and the JWT wiring above.
