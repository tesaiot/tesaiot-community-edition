# Community Edition notes

React live-streaming dashboard that subscribes to device telemetry over
**MQTT-over-WebSocket** and plots it in real time. Ported to Community Edition; the build
is verified (`npm run build`) and the CE WS path was verified independently (a client
connects to `ws://localhost:8083/mqtt` with device credentials, subscribes, and receives
published telemetry — the message also lands in TimescaleDB via the bridge).

## CE adaptations applied
- **Broker:** `wss://mqtt.tesaiot.com:8085/mqtt` → `ws://localhost:8083/mqtt`
  (CE's MQTT-over-WS listener). Port 8085/WSS does not exist on CE.
- **Auth:** removed the cloud-only `tesa_mqtt_` API-token model (username = password =
  token). CE uses **per-device username/password** — the panel now takes a device id and
  its MQTT password, and sets the MQTT **client id = device id** (CE's ACL keys off it).
- **Topic/ACL:** a device credential is scoped by CE's ACL to its **own** topic, so this
  is a per-device live view. A fleet-wide view needs a privileged/service MQTT account.

## Run

```bash
npm install
npm run dev          # serve over http so a plain ws:// broker is allowed (no mixed content)
```

Provision a serverTLS device, get its password from
`POST /api/v1/devices/<id>/reset-mqtt-password`, and enter the device id + password in the
Connection panel.

> Served over **https**, browsers block a plain `ws://` connection (mixed content). For an
> https deployment, provision an EMQX WSS listener fronted by nginx/APISIX TLS and point
> `brokerUrl` at `wss://<host>/mqtt`.

## Verified live stream + fleet view (CE)

The dashboard was verified **live** against CE: a real serverTLS device published over
MQTTS (:8884) while the dashboard, connected to MQTT-over-WS (:8083), charted the stream
in real time. Two CE-specific behaviours matter:

- **Payload envelope:** CE devices publish `{"device_id", "timestamp", "data": {...}}`;
  the hook flattens the inner `data` object so the chart sees the metrics.
- **Watching a live device needs a service account.** CE's auth + ACL key off the MQTT
  client id, so a viewer using the device's own credential collides with the device
  (session takeover). Connect the dashboard with an internal service credential instead —
  username/client-id starting with `mqtt-bridge` (e.g. `mqtt-bridge-dashboard`) and
  `MQTT_BRIDGE_PASSWORD` from the platform `.env` — and set Topic to `device/+/telemetry`
  for a fleet-wide view. Per-device credentials still work for a device watching itself.

## Snapshot (real data from a live CE run)

![live streaming dashboard receiving a real device stream](../../images/screenshots/live-streaming-dashboard.png)
