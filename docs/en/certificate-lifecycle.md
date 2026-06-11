<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Certificate Life-cycle (HashiCorp Vault PKI)

All certificates in TESAIoT Community Edition are issued from a private,
two-tier PKI inside HashiCorp Vault. This document covers the hierarchy, the
roles, and how to **issue**, **renew**, and **revoke** certificates.

---

## 1. The PKI hierarchy

`init-vault-pki.sh` builds this on first install:

```
pki-root   (TESAIoT Community Edition Root CA)          RSA-4096, TTL 87600h (10y)   — offline-style root
   └── signs ──►
pki-int    (TESAIoT Community Edition Intermediate CA)  RSA-4096, max TTL 43800h (5y) — the ISSUING CA
                 └── issues ──► device, EMQX, and platform-service certs
```

- `VAULT_PKI_PATH=pki-int` is the **issuing** engine the API and vault-agent use.
- The root only ever signs the intermediate; everything operational is issued by
  `pki-int`.
- Both publish CA + CRL distribution URLs under
  `http://tesa-vault:8200/v1/pki-{root,int}/{ca,crl}`.

---

## 2. PKI roles

`init-vault-pki.sh` creates these roles on `pki-int`:

| Role | Key | Usage | TTL (default / max) | For |
|------|-----|-------|---------------------|-----|
| `iot-device-ecc` | EC P-256 | client auth | 8760h / 8760h | mTLS device certs (ECC). |
| `device-cert` | any | client auth | 720h / 8760h | Generic device cert signing. |
| `csr-signing` | any | client + server | 8760h / 26280h | Devices submit their own CSR (uses CSR CN/SANs). |
| `emqx-server` | RSA-2048 | server + client | 2160h / 8760h | EMQX broker server cert. |
| `emqx-server-ecdsa` | EC P-256 | server + client | 2160h / 8760h | EMQX broker server cert (ECDSA). |
| `platform-service` | RSA-2048 | server + client | 2160h / 8760h | nginx / apisix / mqtt-bridge / generic service certs. |

Device-domain SANs default to `device.tesa.local` plus `DOMAIN` and `localhost`
(override with `VAULT_PKI_DEVICE_DOMAIN`).

---

## 3. Who holds which credential

| Principal | Auth to Vault | Policy | Can do |
|-----------|---------------|--------|--------|
| **API** (`tesa-api`) | token rendered by vault-agent at `config/vault-agent/token-api/api-token` | `api-pki` (`config/vault-policies/api-csr-signing.hcl`) | issue/sign device certs, read CA, revoke, store cert KV. |
| **vault-agent** | AppRole `api-service` (role-id/secret-id under `config/vault-agent/secrets-unified/`) | `api-pki` | render & renew the EMQX server cert and the API token. |
| **Operator** | `VAULT_ROOT_TOKEN` from `.env` | root | everything (use sparingly). |

The normal path is: **operators use the Admin UI / API**, which uses its
vault-agent-supplied token. Direct `vault` CLI is only for break-glass / setup.

---

## 4. Issue a certificate

### 4.1 Through the platform (normal path)

Register a device in the Admin UI or via the API and request a certificate; the
API calls Vault PKI for you and stores the metadata in MongoDB
(`certificates` collection + `device.certificate_serial`). See
[device-management.md](device-management.md).

### 4.2 Directly from Vault (operator / scripting)

Issue an ECC client cert for a device (Vault generates the key):

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" \
  tesa-vault vault write -format=json pki-int/issue/iot-device-ecc \
  common_name="sensor-01.device.tesa.local" ttl="8760h"
# returns: certificate, private_key, ca_chain, serial_number
```

Sign a device-supplied CSR (device keeps its private key):

```bash
docker exec -i -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" \
  tesa-vault vault write -format=json pki-int/sign/csr-signing \
  csr=- common_name="sensor-01.device.tesa.local" ttl="8760h" < device.csr
```

Issue a server cert (e.g. for nginx/EMQX/APISIX):

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" \
  tesa-vault vault write -format=json pki-int/issue/platform-service \
  common_name="$DOMAIN" alt_names="localhost,mqtt.$DOMAIN" ip_sans="127.0.0.1" ttl="2160h"
```

---

## 5. Renew a certificate

Vault PKI certificates are **short-lived and re-issued**, not renewed in place.

- **EMQX server cert** — fully automatic. The `vault-agent`'s
  `agent-cert-renewal.hcl` template re-renders the cert when it nears expiry
  (`NEXT_SECS=604800` → renews ~7 days before expiry, checked every
  `SLEEP_SECS=43200` ≈ 12h), and reloads EMQX.
- **API token** — auto-renewed by vault-agent.
- **Device certs** — issue a fresh cert (section 4) before the old one expires
  and roll it to the device. Track expiry from the `certificates` collection or
  the Device Details view.

To force a re-render of agent-managed certs:

```bash
docker compose restart vault-agent
```

---

## 6. Revoke a certificate

Revoke by serial number (the API exposes this via
`CertificateManagerVault.revoke_certificate(serial, reason)`; you can also do it
directly):

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" \
  tesa-vault vault write pki-int/revoke serial_number="<serial>"
```

After revocation:

1. Vault updates the CRL at `pki-int/crl`.
2. Mark the device disabled / re-issue a new cert in the registry so the API
   stops authorizing the old identity.
3. For immediate enforcement at the broker/edge, the API's device-authorization
   check (keyed on serial / CN against MongoDB) rejects revoked identities even
   before clients refresh the CRL.

Rotate the CRL / inspect issued certs:

```bash
docker exec -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" tesa-vault vault read pki-int/crl/rotate
docker exec -e VAULT_TOKEN="$VAULT_ROOT_TOKEN" tesa-vault vault list pki-int/certs
```

---

## 7. Operational notes

- **Back up Vault.** The unseal keys + root token live in `.env`; the PKI data
  lives in the `vault-data` volume. `make backup` captures both. Without the
  unseal keys you cannot recover the CA.
- **Protect `.env`** — it is the single most sensitive file (unseal keys, root
  token, all passwords).
- **Rotate the intermediate** before its 5-year max TTL by re-running the
  intermediate generation/sign steps (advanced; coordinate with device cert
  re-issuance).
- The first-run self-signed certs in `config/tls/` are **not** part of this PKI;
  replace them with `platform-service`-issued certs for production (see
  [security-tls-mtls.md](security-tls-mtls.md) §4).
