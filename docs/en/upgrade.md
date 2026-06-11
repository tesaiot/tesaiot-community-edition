<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Upgrade Guide

TESAIoT Community Edition follows [Semantic Versioning](https://semver.org) and
records every change in [`CHANGELOG.md`](../../CHANGELOG.md) (Keep a Changelog
format). The current version is in [`VERSION.txt`](../../VERSION.txt).

- **PATCH** (`1.0.x`) — backward-compatible fixes; upgrade freely.
- **MINOR** (`1.x.0`) — backward-compatible features; review the changelog.
- **MAJOR** (`x.0.0`) — may contain breaking changes; **read the migration
  notes in the changelog before upgrading.**

---

## 1. Before you upgrade

1. **Read the changelog** for every version between yours and the target,
   especially the **Changed**, **Removed**, **Deprecated** and **Security**
   sections.
2. **Back up.** Always:
   ```bash
   make backup
   ```
   Keep the archive off-host. For major upgrades, also snapshot the data volumes
   (see [backup-restore.md](backup-restore.md) §4).
3. **Note your customisations** — any edits to files under `config/`,
   `docker-compose.yml`, or `.env` so you can re-apply or merge them.

---

## 2. Standard upgrade procedure

```bash
cd tesaiot-community-edition

# 1. Back up first
make backup

# 2. Get the new version
git fetch
git checkout v<new-version>        # or: git pull on your release branch

# 3. Reconcile config changes
#    Compare the new template against your live .env and merge any NEW keys.
diff .env.example .env || true
#    Review changes to config/ and docker-compose.yml from the diff/changelog.

# 4. Rebuild images and apply
make build
make up                            # recreates only changed containers

# 5. Run any init steps (all idempotent)
make init-pki                      # picks up new PKI roles if added
make init-db                       # applies new schema if added
make init-emqx
make init-apisix

# 6. Verify
make health
```

> `docker compose up -d` recreates only containers whose image or config
> changed; untouched services keep running. Named volumes (databases, Vault) are
> **preserved** across `make build` / `make up` / `make down`.

---

## 3. Merging configuration changes

A new release may add `.env` keys or change config files:

- **New `.env` keys** — compare `.env.example` (new) with your `.env` and add any
  missing keys with sensible values. Existing secrets are untouched.
- **Secret-bearing config files are rendered from `*.tpl` templates.** The files
  `config/emqx/emqx.conf`, `config/apisix/config.yaml`,
  `config/apisix/apisix.yaml`, `config/emqx/auth-built-in-db-bootstrap.csv` and
  `config/nginx/conf.d/30-iot-mtls.conf` are **generated** (and git-ignored):
  `generate-secrets.sh` re-renders each one from its versioned `<name>.tpl`
  template on every run, injecting secrets from `.env`. **Do not edit the
  rendered files — your changes are overwritten on the next render.** To
  customise one, edit its `.tpl` template instead, then re-run
  `./scripts/generate-secrets.sh` (it is idempotent). After pulling a new
  release, review upstream changes to the `*.tpl` templates and re-render.
- **Other `config/` files** (mounted read-only, not templated) — if you
  customised one, merge the upstream changes into your copy.

---

## 4. Database & schema migrations

- **TimescaleDB** — `init-timescale.sql` uses `IF NOT EXISTS` / `if_not_exists`,
  so re-running `make init-db` safely adds new tables/indexes/aggregates without
  touching existing data.
- **MongoDB** — collections and indexes are created idempotently by
  `init-mongo.js` on first DB init. New collections/indexes added in a release
  may need a one-off command if your DB already exists; the changelog will call
  this out.

Always take a backup before any schema change so you can roll back.

---

## 5. Rolling back

If an upgrade misbehaves:

```bash
# 1. Return to the previous version
git checkout v<previous-version>

# 2. Rebuild and bring up
make build && make up

# 3. If data needs reverting, restore the pre-upgrade backup
make restore FILE=backups/tesaiot-community-edition-<pre-upgrade-timestamp>.tar.gz
make restart
make health
```

Downgrades are only safe back to a version compatible with your current
on-disk data; when in doubt, restore the matching backup taken before the
upgrade.

---

## 6. Upgrading the underlying images

The pinned image versions live in `docker-compose.yml` (Vault, MongoDB,
TimescaleDB, Redis, EMQX, nginx, APISIX). To move to a newer base image:

1. Back up.
2. Bump the `image:` tag in `docker-compose.yml`.
3. Review that vendor's release notes for breaking changes (especially major
   MongoDB / PostgreSQL / EMQX jumps, which can require their own migration).
4. `make build && make up && make health`.

Pin to specific patch versions (as shipped) rather than `latest` for
reproducible, auditable deployments.
