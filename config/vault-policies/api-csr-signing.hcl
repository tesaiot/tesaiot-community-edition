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

# Direct issuance, enumerated rather than wildcarded so every grant is visible.
#
# READ THIS BEFORE TRUSTING THE SHAPE OF THIS FILE. The device roles below are
# what the API itself uses: certificate_service.py hardcodes 'iot-device-ecc'
# and pki_provisioning_service.py 'device-cert', and both force the common name
# to the device id, so no request can steer issuance to another role.
#
# The SERVER roles below (emqx-server, emqx-server-ecdsa, platform-service) are
# NOT for the API. They are here because the Vault Agent renders the TLS
# material for emqx, nginx, apisix and mqtt-bridge from its templates, and the
# agent authenticates with the SAME AppRole ('api-service') whose token the API
# then reads from the agent's sink. One identity, two consumers — so this policy
# is the union of what both need, and a token stolen from either could mint a
# server certificate and impersonate a platform endpoint.
#
# Removing the server roles here does NOT fix that: it breaks TLS for every
# service the agent provisions. The fix is privilege separation — give the agent
# its own AppRole and policy for the server roles, leave the API with the device
# roles only — which changes the provisioning flow in init-vault-pki.sh and the
# agent config, and is tracked as its own change rather than done inline here.
#
# If you add a new device role in init-vault-pki.sh, add its issue path here.
path "pki-int/issue/device-cert" {
  capabilities = ["create", "update"]
}

path "pki-int/issue/iot-device-ecc" {
  capabilities = ["create", "update"]
}

path "pki-int/issue/emqx-server" {
  capabilities = ["create", "update"]
}

path "pki-int/issue/emqx-server-ecdsa" {
  capabilities = ["create", "update"]
}

path "pki-int/issue/platform-service" {
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
