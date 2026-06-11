<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Troubleshooting

Start with the consolidated probe:

```bash
make health          # status table for every service
make ps              # container states
make logs s=<svc>    # logs for one service, e.g. make logs s=api
```

Service container names: `tesa-vault`, `tesa-vault-agent`, `tesa-mongodb`,
`tesa-timescaledb`, `tesa-redis`, `tesa-api`, `tesa-admin-ui`, `tesa-emqx`,
`tesa-mqtt-bridge`, `tesa-nginx`, `tesa-apisix`.

---

## 1. Install / preflight

**`docker compose v2 plugin missing`**
Install the Compose v2 plugin. The legacy `docker-compose` binary is not
supported. Verify with `docker compose version`.

**`cannot talk to docker daemon`**
Start Docker and ensure your user is in the `docker` group
(`sudo usermod -aG docker $USER`, then re-login).

**`.env still contains CHANGEME placeholders`**
Run `./scripts/generate-secrets.sh` (or `make secrets`) to fill them, or edit
`.env` by hand.

**Port already in use**
Preflight only warns. If a non-stack process owns a port, stop it or change the
host port mapping in `docker-compose.yml`.

---

## 2. Vault

**Vault shows WARN / SEALED in `make health`**
Vault restarted (e.g. the host rebooted) and came back sealed.

- **Normally this self-heals within ~30 s:** the vault-agent side-car watches
  the seal status and unseals automatically using the `VAULT_UNSEAL_KEY_*`
  shares from `.env` (passed in as `VAULT_UNSEAL_KEYS` — see the trade-off
  comment in `docker-compose.yml`; leave the vars empty to opt out).
- **Manual recovery** (self-unseal opted out, or vault-agent itself down):
  ```bash
  make unseal          # ./scripts/unseal-vault.sh - idempotent
  ```
- If the unseal keys are blank in `.env`, Vault was never initialised — run
  `make init-pki` to initialise it (also idempotent; it unseals too).

**API can't issue certificates / `permission denied` from Vault**
The API token may be missing or stale. Re-render it:
```bash
docker compose restart vault-agent
docker exec tesa-vault-agent cat /vault/token/api-token   # should print a token
docker compose restart api
```
If the AppRole credentials are missing
(`config/vault-agent/secrets-unified/role-id`), re-run `make init-pki`.

**Lost `.env` / unseal keys**
Without the unseal keys you cannot unseal existing Vault data. Restore `.env`
from backup (`make restore`) or, if data is expendable, purge and reinstall:
`make teardown MODE=purge && make install`.

---

## 3. MongoDB

**`make init-db` can't reach mongod / replica set not initiated**
Wait for the container to be healthy (`make ps`), then re-run `make init-db`.
Check the keyfile exists and is owned correctly:
```bash
ls -l config/mongodb/mongodb-keyfile     # should be mode 400
```
If the keyfile is wrong, MongoDB won't start the replica set — regenerate with
`./scripts/generate-secrets.sh --force` (destroys other secrets; back up first)
or fix permissions to uid 999.

**Auth failures from the API**
Confirm `MONGODB_USER` / `MONGODB_PASSWORD` in `.env` match what
`init-mongo.js` created. The app user is only created on the **first** DB init;
changing the password in `.env` later does not update Mongo automatically.

---

## 4. TimescaleDB

**`device_telemetry hypertable not found`**
`init-databases.sh` re-applies `init-timescale.sql` automatically. If it still
fails, apply manually:
```bash
docker exec -i tesa-timescaledb psql -U postgres -d tesa_telemetry \
  < config/timescaledb/init-timescale.sql
```

**No telemetry rows appearing** — see §8.

---

## 5. API

**API container unhealthy / restarting**
```bash
make logs s=api
```
Common causes: a dependency (Mongo/Timescale/Redis/Vault) not healthy yet
(it will retry), a wrong secret in `.env`, or a missing Vault token (see §2).
The healthcheck hits `http://localhost:5566/api/v1/health`.

**Login returns 429 (rate limited)**
Per-IP login limiting kicked in. Wait, or restart the API
(`docker compose restart api`) to clear it. The bootstrap admin bypasses it when
`ADMIN_BYPASS_RATE_LIMIT=true`.

---

## 6. nginx / TLS

**Browser certificate warning**
Expected on first run — the certs are self-signed. Replace them with Vault-PKI
or Let's Encrypt certs (see [security-tls-mtls.md](security-tls-mtls.md) §4).

**`nginx -t` fails / 502 from nginx**
```bash
docker exec tesa-nginx nginx -t       # config test
make logs s=nginx
```
A 502 usually means the API/UI upstream isn't up yet — nginx resolves upstreams
at request time, so retry once `make health` shows them `UP`.

---

## 7. EMQX / MQTT

**Device rejected on connect**
Check the auth chain: the API webhook (`/api/v1/emqx/auth`) must be reachable and
share the same `EMQX_WEBHOOK_SECRET`.
```bash
make logs s=emqx
make logs s=api        # look for the /api/v1/emqx/auth call
```

**mTLS handshake fails**
The device cert must be issued by the Vault PKI and the broker must trust the CA
(`/opt/emqx/etc/certs/vault-ca-bundle.pem`, rendered by vault-agent). Re-render
with `docker compose restart vault-agent emqx`.

**Bridge can't connect**
Ensure the `mqtt-bridge` user exists with the password in `MQTT_BRIDGE_PASSWORD`:
```bash
make init-emqx
```

---

## 8. Telemetry not reaching the dashboard

Walk the pipeline:

```bash
make logs s=mqtt-bridge          # is the bridge forwarding?
make logs s=api                  # is /api/v1/telemetry accepting?
docker exec tesa-timescaledb psql -U postgres -d tesa_telemetry -c \
  "SELECT count(*) FROM device_telemetry;"
```

Checklist: device authorized by the ACL webhook → publishing to a topic the
bridge subscribes to → API writing to TimescaleDB. See
[telemetry-dashboard.md](telemetry-dashboard.md) §5.

---

## 9. APISIX

**`429` from the gateway**
Route-level `limit-req` (1000/2000 default; shared across callers of the route,
not per-device in standalone mode). The response includes the reason; raise
`limit-req` in `config/apisix/apisix.yaml.tpl` if legitimate, re-render with
`make secrets` (the mounted `apisix.yaml` is generated from the `.tpl`), then
`docker compose restart apisix`.

**Routes not loading**
CE uses standalone YAML mode — the source of truth is the rendered
`apisix.yaml` (generated from `apisix.yaml.tpl` by `generate-secrets.sh`).
Validate indentation in the `.tpl`, re-render (`make secrets`), ensure the
admin key was injected (`make init-apisix`), and restart.

---

## 10. Full reset

```bash
make down                  # stop, keep data
make teardown MODE=volumes # stop + delete all data volumes
make teardown MODE=purge   # also delete .env / certs / keyfile (start from scratch)
make install               # rebuild from zero
```

If a problem persists, collect `make logs s=<svc>` output and open an issue
(see [SECURITY.md](../../SECURITY.md) for security-sensitive reports).
