# Community Edition notes

n8n workflows for TESAIoT, adapted to a self-hosted Community Edition install. The
workflow JSON is CE-ready (valid, importable); running it requires your own n8n instance.

## CE adaptations applied (`workflows/*.json`)
- Endpoints repointed from `admin.tesaiot.com` / `api.tesaiot.com` → `https://localhost`.
- Dropped the `/api/v1/external` prefix — CE has no `external` blueprint; device reads
  live at `/api/v1/devices`, telemetry at `/api/v1/telemetry`.

## Remaining CE wiring (do this in the n8n UI)
- **Auth:** device/dashboard reads are **JWT-only** on CE. Add an HTTP Request node (or
  credential) that logs in via `POST /api/v1/auth/login` and pass the bearer token to the
  read nodes. The device API key (`X-API-KEY`) authorises telemetry-ingest only.
- **Single org:** remove any `organization_id` parameters — CE is single-organization.
- **Alerts (`device-alert-slack`):** CE emits no inbound anomaly webhook (analytics is
  excluded). Re-architect the trigger to a **schedule poll + threshold IF** node, or an
  MQTT trigger against EMQX, rather than an anomaly webhook.

## Run
Import the JSON into n8n (`docker run -it --rm -p 5678:5678 n8nio/n8n`), set the CE
credentials, and execute. Trust the CE CA or disable TLS verification on the HTTP nodes
for a local self-signed edge.
