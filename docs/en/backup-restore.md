<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Backup & Restore

TESAIoT Community Edition ships `scripts/backup.sh` and `scripts/restore.sh`
(wrapped by `make backup` / `make restore`) to capture and recover everything
needed to rebuild a deployment: both databases plus the secrets and certificate
material.

---

## 1. What a backup contains

`make backup` produces a single, mode-`600` archive at
`backups/tesaiot-community-edition-<timestamp>.tar.gz` containing:

| Item | Source |
|------|--------|
| `mongodb.archive.gz` | `mongodump` (gzip archive) of all MongoDB databases. |
| `timescaledb.dump` | `pg_dump -Fc` of the telemetry database. |
| `vault-data.tar.gz` | snapshot of the `vault-data` volume — **the whole Vault PKI** (CA keys, issued-cert index, KV device certs). |
| `emqx-data.tar.gz` | snapshot of the `emqx-data` volume (built-in auth DB, retained messages). |
| `.env` | All secrets, **including Vault unseal keys + root token**. |
| `config/mongodb-keyfile` | MongoDB replica-set keyfile. |
| `config/tls/` | serverTLS cert/key + CA bundle (incl. the Vault client-CA chain). |
| `config/secrets-unified/` | vault-agent AppRole role-id / secret-id. |
| `config/token-api/` | the API's Vault token. |
| `config/rendered/` | the rendered runtime configs (`emqx.conf`, bootstrap CSV, APISIX `config.yaml`/`apisix.yaml`, nginx `30-iot-mtls.conf`) so they stay in sync with the restored `.env`. |

> **The archive contains live secrets.** Treat it like a password vault: encrypt
> at rest, restrict access, store off-host.

> **Vault note:** the volume snapshots are taken live (crash-consistent). For a
> bit-exact copy stop the stack first and use the volume-level procedure in §4.

---

## 2. Creating a backup

```bash
make backup
# -> backups/tesaiot-community-edition-YYYYMMDD-HHMMSS.tar.gz
```

The stack should be running (the script execs `mongodump` / `pg_dump` inside the
DB containers). Schedule it with cron, e.g. nightly:

```cron
30 2 * * *  cd /path/to/tesaiot-community-edition && /usr/bin/make backup >> logs/backup.log 2>&1
```

Copy the resulting archive to secure off-host storage and prune old ones.

---

## 3. Restoring

For the database dumps to load, `mongodb` + `timescaledb` must be **up**
(everything else in the archive restores fine with the stack down — the script
simply skips the DB load and tells you to re-run it):

```bash
make up                                            # ensure stack is running
make restore FILE=backups/tesaiot-community-edition-YYYYMMDD-HHMMSS.tar.gz
make restart
```

`restore.sh` will:

1. Extract the archive to a temp dir.
2. Restore `.env` (backing up any existing one as `.env.bak.<epoch>`), the mongo
   keyfile, `config/tls/`, the vault-agent AppRole, the API token, and the
   rendered runtime configs.
3. Restore the `vault-data` / `emqx-data` volume snapshots (stopping and
   restarting the owning container around the copy).
4. `mongorestore --drop` the MongoDB archive.
5. `pg_restore --clean --if-exists --no-owner` the TimescaleDB dump.

Then restart the stack so services pick up the restored secrets/certs.

### Restoring onto a fresh host

**Restore FIRST, then build/up.** Running `make up` on a bare clone fails:
compose has no `.env` (empty required variables), the keyfile bind-mount gets
auto-created as a *directory*, and vault-agent has no AppRole credentials. The
first restore pass lays all of that down; the second pass (with the stack up)
loads the database dumps and volume snapshots:

```bash
git clone <repo> && cd tesaiot-community-edition
./scripts/restore.sh <archive>   # 1) .env, keyfile, TLS, approle, rendered configs
make build && make up            # 2) now compose has everything it needs
./scripts/restore.sh <archive>   # 3) DB dumps + vault-data/emqx-data volumes
make unseal                      # 4) unseal the restored Vault (or rely on self-unseal)
make restart && make health
```

Because `.env` (with the Vault unseal keys + root token) and the `vault-data`
snapshot come from the same archive, the restored Vault unseals with the
restored keys and the original CA keeps working — already-issued device certs
stay valid.

---

## 4. Volume-level snapshots (full DR)

For bit-exact disaster recovery of Vault and the databases, snapshot the Docker
volumes while the stack is stopped:

```bash
make down
for v in vault-data vault-credentials mongodb-data timescale-data emqx-data emqx-certs; do
  docker run --rm -v "tesaiot-community-edition_${v}:/data" -v "$PWD/backups:/out" \
    alpine tar -czf "/out/${v}.tar.gz" -C /data .
done
make up
```

(The volume name prefix is the Compose project name — usually the directory
name. Check with `docker volume ls`.)

Restore a volume:

```bash
make down
docker run --rm -v "tesaiot-community-edition_vault-data:/data" -v "$PWD/backups:/in" \
  alpine sh -c 'rm -rf /data/* && tar -xzf /in/vault-data.tar.gz -C /data'
make up
```

---

## 5. Restore checklist

- [ ] Stored the archive off-host and encrypted.
- [ ] Verified `.env` restored (and the previous one backed up).
- [ ] `make health` shows all services `UP`.
- [ ] Vault is unsealed (`docker exec tesa-vault vault status`).
- [ ] Telemetry visible in Device Details.
- [ ] Test login with a known user.
