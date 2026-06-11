<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# IoT Telemetry Dashboard

The Telemetry Dashboard is the live time-series view built into the **Device
Details** page of the Admin UI. It is the single dashboard included in the CE
distribution (the separate analytics / Grafana modules are out of scope).

---

## 1. Where it lives

```
Admin UI → Devices → (select a device) → Device Details → Telemetry tab
```

It shows, for the selected device:

- Latest metric values and connection status.
- Time-series charts per metric (temperature, humidity, custom metrics, …).
- Selectable time windows, backed by TimescaleDB continuous aggregates for
  fast rendering.

---

## 2. Data model (TimescaleDB)

Telemetry is stored in the `device_telemetry` hypertable
(`config/timescaledb/init-timescale.sql`):

| Column | Type | Notes |
|--------|------|-------|
| `time` | `TIMESTAMPTZ` | hypertable time dimension (1-day chunks). |
| `device_id` | `VARCHAR(255)` | device key. |
| `organization_id` | `VARCHAR(255)` | always `DEFAULT_ORG_ID` in CE. |
| `metric_name` | `VARCHAR(100)` | e.g. `temperature`. |
| `metric_value` | `DOUBLE PRECISION` | the value. |
| `unit` | `VARCHAR(50)` | optional. |
| `location` / `metadata` | `JSONB` | optional. |

Performance helpers created automatically:

- Indexes on `(device_id, time)`, `(organization_id, time)`, `(metric_name, time)`.
- Continuous aggregate **`device_metrics_1min`** (avg/min/max/count per minute),
  refreshed every minute — the dashboard reads this for smooth charts.
- Retention policy: raw telemetry kept **90 days**, events **180 days** (tune in
  the SQL or with `add_retention_policy`).

---

## 3. How data gets in

```
Device --MQTT--> EMQX --> mqtt-bridge --> POST /api/v1/telemetry --> TimescaleDB (+ MongoDB)
Device --HTTPS (APISIX :9443 / nginx :9444)--> POST /api/v1/telemetry --> TimescaleDB
```

The API enables dual storage (`ENABLE_DUAL_STORAGE=true`) and auto-creates the
schema if missing (`ENABLE_AUTO_TIMESCALE_SCHEMA=true`).

---

## 4. Reading telemetry via the API

The dashboard uses these endpoints (admin JWT):

| Method & path | Purpose |
|---------------|---------|
| `GET /api/v1/devices/<id>/telemetry` | Time-series for a device (range/metric filters). |
| `GET /api/v1/devices/<id>/telemetry/last` | Most recent reading(s). |
| `GET /api/v1/telemetry/unified/<id>` | Unified telemetry view for a device. |
| `GET /api/v1/telemetry/availability/summary` | Availability summary. |
| `GET /api/v1/telemetry/health` | Telemetry subsystem health. |

Example:

```bash
TOKEN=<admin access_token>
curl -k "https://localhost/api/v1/devices/sensor-01/telemetry?metric=temperature&from=-1h" \
  -H "Authorization: Bearer $TOKEN"
```

Live updates stream to the UI over the WebSocket-upgraded `/api` path (nginx
`20-admin-api.conf` enables `Upgrade`/`Connection` headers).

---

## 5. Verifying telemetry end-to-end

```bash
# 1. Publish a test reading (serverTLS)
mosquitto_pub -h localhost -p 8884 --cafile config/tls/ca-bundle.pem \
  -u sensor-01 -P "<device-password>" \
  -t "devices/sensor-01/telemetry" -m '{"temperature":24.1}'

# 2. Confirm it landed in TimescaleDB
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -c \
  "SELECT time, device_id, metric_name, metric_value
     FROM device_telemetry ORDER BY time DESC LIMIT 5;"

# 3. Open Device Details → Telemetry tab and confirm the chart updates.
```

If nothing appears, check `make logs s=mqtt-bridge` and `make logs s=api`, and
see [troubleshooting.md](troubleshooting.md).

---

## 6. Tuning

- **Chunk interval / retention** — edit `config/timescaledb/init-timescale.sql`
  (for a fresh DB) or run `SELECT set_chunk_time_interval(...)` /
  `add_retention_policy(...)` on the live DB.
- **Aggregate granularity** — add more continuous aggregates (e.g. 5-min, 1-hour)
  for longer time ranges.
- **Audit tables** — `activity_logs` / `security_logs` hypertables are optional;
  nothing else depends on them and they can be dropped if unused.
