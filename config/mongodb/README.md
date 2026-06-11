# MongoDB configuration (TESAIoT Community Edition)

Single-organization MongoDB setup. MongoDB runs as a single-node replica set
(`rs0`) so the application can use replica-set / transaction semantics, with
keyFile internal authentication enabled.

## Files

- `init-mongo.js` — runs once on first container start (mounted into
  `/docker-entrypoint-initdb.d/`). Creates the application user, the in-scope
  collections, and a single default organization. Reads `MONGODB_USER`,
  `MONGODB_PASSWORD`, `MONGO_INITDB_DATABASE`, and `DEFAULT_ORG_ID` from the
  environment — the SAME `MONGODB_USER` / `MONGODB_PASSWORD` the API uses to
  connect (see `services/api/api/core/db_config.py`), so a fresh `make install`
  produces an app user the API can actually authenticate as. The script fails
  closed and refuses to create the user if `MONGODB_PASSWORD` is unset.
- `mongodb-keyfile` — **NOT shipped.** Must be generated at deploy time (see
  below). It is intentionally absent from this distribution; never commit a real
  keyfile.

## Generate the keyfile (required before first start)

The keyfile is a 1024-byte base64 shared secret for replica-set member auth.
Generate it next to this README and lock down its permissions:

```bash
openssl rand -base64 756 > config/mongodb/mongodb-keyfile
chmod 400 config/mongodb/mongodb-keyfile
# The mongo image runs as uid/gid 999; make sure it can read the file:
sudo chown 999:999 config/mongodb/mongodb-keyfile
```

The compose service mounts it read-only at `/data/mongo-keyfile` and starts
`mongod` with `--replSet rs0 --keyFile /data/mongo-keyfile`.

## One-time replica-set initiation

A single-node replica set must be initiated once after the first start:

```bash
docker exec -it tesa-mongodb mongosh -u "$MONGO_INITDB_ROOT_USERNAME" \
  -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin \
  --eval 'rs.initiate()'
```

After that, the API connects via `MONGODB_URI` with `replicaSet=rs0`.

## Secrets

No secrets are stored in this directory. Set the following in the root `.env`:

- `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD` (root user, created
  by the mongo image)
- `MONGODB_USER` / `MONGODB_PASSWORD` (application user, created by
  `init-mongo.js` and used by the API to connect; `MONGODB_PASSWORD` is required)
- `MONGO_INITDB_DATABASE` (default `tesa_iot`)
- `DEFAULT_ORG_ID` (default `default`)
