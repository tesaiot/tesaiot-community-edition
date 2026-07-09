# Community Edition notes

React/Vite telemetry dashboard, ported to a self-hosted Community Edition install. The
build and its live CE data flow are **verified**: `npm run build` succeeds, and the API
layer (login → device list → telemetry) was exercised against a running CE
(`/api/v1/auth/login` → `/api/v1/devices/` → `/api/v1/telemetry/unified/{id}`, all 200).

## CE adaptations applied (`src/api/tesaiotApi.ts`)
- Base URL from `VITE_API_BASE_URL` (default `https://localhost`) — was hardcoded
  `admin.tesaiot.com`.
- **Removed the committed API key.** CE gates device/telemetry reads behind **JWT**, not a
  static API key, so the client logs in (`/api/v1/auth/login`) and sends a Bearer token.
  Credentials come from `VITE_ADMIN_EMAIL`/`VITE_ADMIN_PASSWORD` (or `VITE_JWT`) — never
  committed.
- Endpoints rewritten to CE: device list `/api/v1/devices/` (bare array), telemetry
  `/api/v1/telemetry/unified/{id}` (returns `data_points`), with response-shape mapping.
- **AI overlay degrades gracefully.** CE excludes the AI/analytics module
  (`has_ai_data: false`), so `fetchAIResults` returns an empty list and the AI chart layer
  stays inert.

## Run

```bash
npm install
# copy .env.example to .env and set VITE_API_BASE_URL + credentials
npm run dev       # or: npm run build && preview
```

> The dashboard talks to CE over HTTPS. For local dev against a self-signed edge, either
> trust the CE CA (`config/tls/ca-bundle.pem`) in your browser or run the dashboard behind
> the same origin.

## Chart library (CE change)

The upstream example rendered with plotly.js, which does not bundle reliably with Vite —
in a production build the chart silently draws no traces. The CE port re-implements
`EdgeAIChart` with **recharts** (the same library the CE Admin UI uses): multi-series
lines, automatic dual Y-axis when magnitudes differ (e.g. pressure vs temperature), and
the AI overlay only when `ai_*` fields exist (never on stock CE). Verified end-to-end —
the snapshot below is real telemetry fetched from a live CE install.

## Snapshot (real data from a live CE run)

![react telemetry dashboard with real CE data](../../images/screenshots/react-telemetry-dashboard.png)
