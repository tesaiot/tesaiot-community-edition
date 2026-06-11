# HashiCorp Vault + PKI (TESAIoT Community Edition)

Single-organization Vault configuration for the self-hosted Community Edition.
Vault is the certificate authority for the in-scope capabilities:

- serverTLS / mTLS for EMQX, APISIX and nginx
- Device certificate lifecycle (issue / sign-CSR / renew / revoke)

## Files

| Path | Purpose |
|------|---------|
| `vault/vault-auto-unseal.hcl` | Production server config (mounted as `vault.hcl`). File storage, single-node, OSS-safe. |
| `vault/vault.hcl` | Minimal server config alternative. |
| `vault/vault-dev.hcl` | Development server config. |
| `vault-policies/api-csr-signing.hcl` | Policy for the tesa-api service token. |
| `vault-policies/vault-agent.hcl` | Policy for the Vault Agent AppRole. |
| `vault-agent/vault-agent.hcl` | Unified agent: api-token sink + EMQX RSA/ECDSA certs. |
| `vault-agent/{emqx,apisix,nginx,mqtt-bridge}-vault-agent.hcl` | Per-service standalone agent variants. |
| `vault-agent/agent-cert-renewal.hcl` | Optional device certificate auto-renewal agent. |
| `vault-agent/templates/*` | consul-template files (all target the two-tier `pki-int`). |
| `vault-agent/scripts/*` | Render hooks (split bundle, reload EMQX, auto-rotate loop, device renew). |

## PKI Hierarchy (two-tier)

```
pki-root  (Root CA, read-only at runtime)
   └── pki-int  (Intermediate CA, issues all leaf certs)
```

In-scope roles (create these during bootstrap):

| Role | Path | Used by |
|------|------|---------|
| `emqx-server`       | `pki-int/issue/emqx-server`        | EMQX RSA server cert |
| `emqx-server-ecdsa` | `pki-int/issue/emqx-server-ecdsa`  | EMQX ECDSA server cert (dual-cert) |
| `platform-service`  | `pki-int/issue/platform-service`   | APISIX / nginx / internal services |
| `iot-device-ecc`    | `pki-int/issue/iot-device-ecc`     | Device leaf certs (mTLS) |
| `csr-signing`       | `pki-int/sign/csr-signing`         | Sign device-supplied CSRs (mTLS) |

## Bootstrap (one-time)

1. Start Vault, initialize and unseal (the auto-unseal script in
   `scripts/vault-init/` stores the root token under `/vault/credentials`).
2. Enable and build the PKI hierarchy (root `pki-root`, intermediate `pki-int`,
   sign-intermediate, set issuing/CRL URLs).
3. Create the roles listed above.
4. Write the policies:
   ```bash
   vault policy write api-csr-signing config/vault-policies/api-csr-signing.hcl
   vault policy write vault-agent     config/vault-policies/vault-agent.hcl
   ```
5. Enable AppRole and create the agent role bound to `vault-agent`, then write
   the generated `role_id` / `secret_id` into
   `config/vault-agent/secrets-unified/{role-id,secret-id}`
   (these ship as `CHANGEME` placeholders).

## Secrets

`secrets-unified/{role-id,secret-id}` and `token-api/api-token*` ship as
`CHANGEME` placeholders and are `.gitignore`d. Never commit real credentials.

## Environment variables consumed by templates

- `EMQX_CERT_CN`        e.g. `mqtt.localhost`
- `EMQX_CERT_ALT_NAMES` e.g. `localhost,tesa-emqx`
- `EMQX_CERT_IP_SANS`   e.g. `127.0.0.1`
- `DEVICE_ID`           (device cert auto-renewal only)
