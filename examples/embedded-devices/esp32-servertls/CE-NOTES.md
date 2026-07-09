# Community Edition notes

ESP32 Arduino firmware that publishes telemetry to CE over **serverTLS** (EMQX `:8884`).

## CE adaptation applied
- `config.h.example`: `MQTT_HOST` → `localhost`, port stays `8884`.
- Paste the CE CA into `ca_cert.h` (from `config/tls/ca-bundle.pem`) so the device
  verifies the broker.
- Provision a serverTLS device and set `DEVICE_ID` / `MQTT_USERNAME` (= device id) /
  `MQTT_PASSWORD` (from `reset-mqtt-password`).

## Verification
This firmware needs an ESP32 to flash, so its **protocol contract** was verified instead:
the exact topic (`device/<id>/telemetry`), payload
(`{"device_id","timestamp","data":{"temperature","humidity"}}`), serverTLS transport, and
username/password auth were reproduced on a host simulator and confirmed landing in the CE
`device_telemetry` hypertable. Flashing real hardware exercises the identical path. See
`TESAIoT_PLAN/examples-vv-evidence.md` §5.

## Snapshot (real data from a live CE run)

![esp32-servertls telemetry contract in CE Device Details](../../images/screenshots/esp32-servertls-telemetry.png)
