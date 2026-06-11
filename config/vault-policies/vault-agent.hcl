# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent policy (single-org)
#
# The Vault Agent authenticates via AppRole and renders service certs
# (EMQX, APISIX, nginx) from the intermediate PKI, plus a renewable API
# token sink for the tesa-api service.

# Issue service / device certificates from the intermediate CA
path "pki-int/issue/*" {
  capabilities = ["create", "update"]
}

# Read the root + intermediate CA so templates can build the full chain
path "pki-root/cert/ca" {
  capabilities = ["read"]
}

path "pki-int/cert/ca" {
  capabilities = ["read"]
}

path "pki-int/cert/ca_chain" {
  capabilities = ["read"]
}

# Inspect / renew its own token (used by the api-token-info.json template)
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
