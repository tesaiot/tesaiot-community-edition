<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# MQTT Telemetry Simulator (Python)

Publishes a continuous stream of simulated sensor telemetry (temperature, humidity,
pressure, plus periodic out-of-range spikes) to **TESAIoT Community Edition** over
serverTLS MQTT. Useful for populating the telemetry dashboard and exercising ingest.

> Verified end-to-end against a live CE install — the stream lands in the
> `device_telemetry` TimescaleDB hypertable.

## Run

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
# copy .env.example to .env and fill in DEVICE_ID + credentials
set -a; . ./.env; set +a
./.venv/bin/python main.py
```

Provision a serverTLS device first (Admin UI or API), then set `MQTT_PASSWORD` from
`POST /api/v1/devices/{id}/reset-mqtt-password`.

## Community Edition notes

- CE's EMQX rejects anonymous / plaintext clients — this port adds `MQTT_USE_TLS`
  (serverTLS 8884 with CA verification) and username/password auth.
- **`MQTT_CLIENT_ID` must equal the device id** — the CE publish ACL authorises
  `device/<client_id>/telemetry` by client id.
- The upstream example was framed as an "Edge-AI / Infineon" simulator; CE excludes the
  AI/analytics module, so this is a plain telemetry simulator — the out-of-range values it
  emits are ordinary telemetry, with no anomaly-detection backend implied.
