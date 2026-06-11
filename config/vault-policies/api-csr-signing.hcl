# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - API / PKI policy (single-org)
#
# Grants the API service the permissions needed for the in-scope
# certificate lifecycle (issue / sign / revoke) against the two-tier
# PKI hierarchy (pki-root -> pki-int) plus KV storage for device certs.

# =============================================================================
# PKI Intermediate CA - issue / sign / revoke
# =============================================================================

# CSR signing (mTLS device certs issued from a device CSR)
path "pki-int/sign/csr-signing" {
  capabilities = ["create", "update"]
}

path "pki-int/sign/device-cert" {
  capabilities = ["create", "update"]
}

# Fallback sign role the API's CSR path may try when csr-signing is rejected.
path "pki-int/sign/iot-device-ecc" {
  capabilities = ["create", "update"]
}

# Direct issuance - DEVICE roles only, enumerated on purpose. The API code
# (services/api: certificate_service.py, pki_provisioning_service.py) issues
# exclusively from 'device-cert' with 'iot-device-ecc' as fallback; a wildcard
# here would also let a compromised API token mint SERVER certs from the
# emqx-server / platform-service roles and impersonate platform endpoints.
# If you add a new device role in init-vault-pki.sh, add its issue path here.
path "pki-int/issue/device-cert" {
  capabilities = ["create", "update"]
}

path "pki-int/issue/iot-device-ecc" {
  capabilities = ["create", "update"]
}

# Revocation + CRL
path "pki-int/revoke" {
  capabilities = ["create", "update"]
}

# Read the intermediate CA cert / chain and any issued certificate
path "pki-int/cert/ca" {
  capabilities = ["read"]
}

path "pki-int/cert/ca_chain" {
  capabilities = ["read"]
}

path "pki-int/cert/*" {
  capabilities = ["read", "list"]
}

# =============================================================================
# PKI Root CA - read-only (trust anchor)
# =============================================================================

path "pki-root/cert/ca" {
  capabilities = ["read"]
}

# =============================================================================
# KV v2 Secrets Engine - Device Certificate storage
# =============================================================================

path "secret/data/pki-devices/certs/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "secret/data/pki-devices/keys/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "secret/metadata/pki-devices/*" {
  capabilities = ["read", "list"]
}

# =============================================================================
# Token self-management
# =============================================================================

path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
