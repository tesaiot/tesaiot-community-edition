<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Security: serverTLS and mTLS

TESAIoT Community Edition supports two device authentication modes. Both are
available simultaneously — you choose per device (or per fleet) which to use.

| Mode | What the device proves | Transport | Best for |
|------|------------------------|-----------|----------|
| **serverTLS** | Server identity only; the device authenticates with **username/password** over an encrypted channel. | MQTT `:8884`, HTTPS `:443` | Simpler devices, gradual rollout, password-managed fleets. |
| **mTLS** | Both sides present certificates; the device proves identity with a **Vault-PKI client certificate**. | MQTT `:8883`, HTTPS `:9444` | Production, high-assurance, passwordless device identity. |

In **both** modes the connection is encrypted (TLS 1.2 / 1.3). The difference is
*who proves identity with a certificate*.

---

## 1. serverTLS

The server presents a certificate the client trusts; the client does **not**
present one. The device then authenticates at the application layer.

### Where it is configured

- **HTTPS / Admin UI / API** — `config/nginx/conf.d/20-admin-api.conf`
  (`listen 443 ssl`, `ssl_certificate` + `ssl_certificate_key`, no client cert).
- **MQTT** — `listeners.ssl.servertls` on `:8884` in `config/emqx/emqx.conf`
  (`verify = verify_none`, `fail_if_no_peer_cert = false`). Devices connect with
  a username/password that EMQX validates via the API auth webhook.
- **API gateway** — the `ssls` block in `config/apisix/apisix.yaml`.

### Connecting a device (serverTLS MQTT)

```bash
mosquitto_pub \
  -h <DOMAIN> -p 8884 \
  --cafile ca-bundle.pem \
  -u "<device-username>" -P "<device-password>" \
  -t "devices/<device-id>/telemetry" \
  -m '{"temperature": 23.5}'
```

EMQX calls `POST /api/v1/emqx/auth` on the API, which verifies the credentials
against the device registry in MongoDB.

---

## 2. mTLS (mutual TLS)

Both the server and the device present certificates. The device's client
certificate is issued by the Vault PKI intermediate CA; the server verifies it
against the CA bundle and then the API authorizes the specific device.

### Where it is configured

- **HTTPS device ingest** — `config/nginx/conf.d/30-iot-mtls.conf` (rendered
  from the committed `.tpl`; `listen 9444 ssl`). Key directives:
  ```nginx
  ssl_client_certificate /etc/nginx/certs/ca-bundle.pem;  # bootstrap CA + Vault PKI chain
  ssl_verify_client      on;   # REQUIRE a verifiable client cert (FAIL CLOSED)
  ssl_verify_depth       2;
  ```
  `ca-bundle.pem` starts life as the bootstrap self-signed CA
  (`generate-secrets.sh`); `init-vault-pki.sh` then **appends the Vault
  root + intermediate chain** to it — that appended chain is what actually
  validates device certificates. After the handshake, nginx forwards the
  verification result and certificate details to the API as headers:
  `X-Client-Verify`, `X-Client-Cert`, `X-Client-S-DN`, `X-Client-Serial`,
  `X-Client-Fingerprint`, etc., plus the `X-MTLS-Gateway` marker. The API uses
  these for per-device authorization.

  - `ssl_verify_client on` (the shipped default) → strict: nginx aborts the
    TLS handshake for any client without a cert that chains to the bundle.
  - Changing it to `optional` would allow a mixed fleet (the API decides per
    request), at the cost of the fail-closed guarantee — not recommended.

- **MQTT** — `listeners.ssl.mtls` on `:8883` in `config/emqx/emqx.conf`:
  ```
  verify = verify_peer
  fail_if_no_peer_cert = true
  cacertfile = /opt/emqx/etc/certs/vault-ca-bundle.pem
  depth = 10
  ```
  EMQX validates the client cert chain, then calls the API auth webhook with
  `cert_common_name` / `cert_subject` so the API can map the cert to a device.

- **API gateway (optional)** — see `config/apisix/mtls-routes.yaml` for ready
  route patterns (add a `client` block with `ca` + `verify_client: true` to the
  `ssls` entry, then merge the routes into `apisix.yaml`).

---

## 3. The device certificate flow

```
1. Operator registers a device           (Admin UI / API)
        │
2. API requests a client cert from Vault  POST pki-int/issue/iot-device-ecc
   PKI (or signs a device-supplied CSR    or  pki-int/sign/csr-signing
   via the csr-signing role)
        │
3. API stores the cert metadata (serial,  MongoDB `certificates` + `devices`
   fingerprint) and returns cert + key    (device.certificate_serial)
   to the operator / device
        │
4. Device installs cert + key + CA bundle
        │
5. Device connects:
     MQTT  :8883  presenting its client cert  ──► EMQX verifies chain ──► API webhook authorizes
     HTTPS :9444  presenting its client cert  ──► nginx verifies ──► API authorizes by serial/CN
        │
6. Renew before expiry / revoke on compromise  (see certificate-lifecycle.md)
```

The certificate identity (CN / serial / fingerprint) is the device's
cryptographic identity; the API ties it to the device record in MongoDB.

---

## 4. Replacing the first-run self-signed certificates

`generate-secrets.sh` writes a **self-signed** CA + server cert to
`config/tls/` so TLS works on first boot. For anything beyond evaluation,
replace them:

### Option A — Vault PKI server certificate

Issue a server cert from the intermediate CA and drop it into `config/tls/`:

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" \
  tesa-vault vault write -format=json pki-int/issue/platform-service \
  common_name="$DOMAIN" alt_names="localhost,mqtt.$DOMAIN" ip_sans="127.0.0.1" \
  ttl=2160h > /tmp/srv.json

# Extract certificate (+ chain) and key into config/tls/
#   .data.certificate  + .data.ca_chain  -> server-cert.pem
#   .data.private_key                    -> server-key.pem
#   .data.issuing_ca                     -> ca-bundle.pem  (client-CA for mTLS)
docker compose restart nginx apisix
```

The CA bundle (`ca-bundle.pem`) is the trust anchor nginx and EMQX use to verify
**client** certs in mTLS, so it must be the Vault PKI issuing CA chain.

### Option B — Let's Encrypt / public CA

Put your fullchain and key at `config/tls/server-cert.pem` /
`config/tls/server-key.pem` (the `10-redirect.conf` server block already serves
the `/.well-known/acme-challenge/` path). Restart nginx. Note: a public CA only
covers serverTLS; mTLS client certs still come from Vault PKI.

---

## 5. TLS hardening already applied

- TLS 1.2 + 1.3 only; explicit modern AEAD-only cipher list (ECDHE +
  AES-GCM/CHACHA20-POLY1305 — no CBC, no SHA-1) on nginx and APISIX, and
  `ssl_session_tickets off`.
- HSTS, `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection` headers
  on the serverTLS vhost.
- `server_tokens off`, request rate-limit zones (`api_limit`, `auth_limit`).
- EMQX modern cipher suites incl. AES-GCM and CHACHA20-POLY1305.
- Per-IP login rate limiting in the API (bypassable only by the bootstrap admin
  if `ADMIN_BYPASS_RATE_LIMIT=true`).

---

## 6. Vault unseal-key custody

In the default single-host install, **all three Shamir unseal keys AND the
root token live in `.env` on the same machine as Vault's data** — and the
vault-agent side-car uses two of them to self-unseal after a reboot
(`VAULT_UNSEAL_KEYS` in `docker-compose.yml`). That is a deliberate
availability trade-off for a self-hosted CE box: anyone who can read `.env`
can unseal Vault anyway.

For production-grade custody:

- **Split the key shares.** Move `VAULT_UNSEAL_KEY_2/3` out of `.env` to
  separate custodians (leaving `VAULT_UNSEAL_KEYS` effectively empty disables
  self-unseal; unsealing then needs two custodians via `make unseal` or
  `vault operator unseal`).
- **Or use cloud-KMS auto-unseal** — uncomment and configure the
  `seal "awskms"` stanza in `config/vault/vault-auto-unseal.hcl`; the unseal
  material then never touches the host.
- Keep the **root token** out of day-to-day use; the platform itself only
  needs the AppRole (vault-agent) and its derived token.
- Off-host **backups** of `.env` (see [backup-restore.md](backup-restore.md))
  are part of the key custody story: treat the archive like the keys.

See also [certificate-lifecycle.md](certificate-lifecycle.md) and
[mqtt-emqx.md](mqtt-emqx.md).
