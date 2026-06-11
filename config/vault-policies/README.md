# Vault Policies (TESAIoT Community Edition)

This directory contains the HashiCorp Vault policy HCL files used by the
self-hosted, single-organization Community Edition.

## Policy Files

| Policy | Bound to | Description |
|--------|----------|-------------|
| `api-csr-signing.hcl` | tesa-api service token (AppRole) | Issue / sign / revoke device & service certs via `pki-int`, store device certs in KV v2 |
| `vault-agent.hcl` | Vault Agent AppRole | Render EMQX / APISIX / nginx certs from `pki-int`, maintain the renewable api-token sink |

## PKI Hierarchy

The CE build uses a two-tier hierarchy:

- `pki-root` — offline-style Root CA (read-only at runtime; trust anchor)
- `pki-int`  — Intermediate CA that issues all leaf certificates

Roles referenced by the policies / agent templates:

- `pki-int/issue/emqx-server`         (RSA EMQX server cert — serverTLS/mTLS)
- `pki-int/issue/emqx-server-ecdsa`   (ECDSA EMQX server cert — dual-cert)
- `pki-int/issue/platform-service`    (APISIX / nginx / internal services)
- `pki-int/issue/iot-device-ecc`      (device leaf certs for mTLS)
- `pki-int/sign/csr-signing`          (sign device-supplied CSRs for mTLS)

## Applying Policies

```bash
# Get the root token (created by the auto-unseal/init flow)
ROOT_TOKEN=$(docker exec tesa-vault cat /vault/credentials/root-token.txt)

# Write a policy
cat config/vault-policies/api-csr-signing.hcl \
  | docker exec -i -e VAULT_TOKEN="$ROOT_TOKEN" tesa-vault \
      vault policy write api-csr-signing -

cat config/vault-policies/vault-agent.hcl \
  | docker exec -i -e VAULT_TOKEN="$ROOT_TOKEN" tesa-vault \
      vault policy write vault-agent -
```

## AppRole Credentials

`config/vault-agent/secrets-unified/{role-id,secret-id}` ship as **placeholders
(`CHANGEME`)**. Generate real values after Vault is initialized:

```bash
vault write -f auth/approle/role/vault-agent token_policies="vault-agent"
vault read  -field=role_id   auth/approle/role/vault-agent/role-id   > config/vault-agent/secrets-unified/role-id
vault write -f -field=secret_id auth/approle/role/vault-agent/secret-id > config/vault-agent/secrets-unified/secret-id
```

Never commit real role-id / secret-id / tokens to the distribution.
