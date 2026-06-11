# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Unified Vault Agent configuration
#
# Purpose: single Vault Agent that serves the in-scope platform services:
#   - tesa-api: renewable token sink (for CSR signing / cert lifecycle)
#   - EMQX:     TLS server certificate issuance and auto-renewal (RSA + ECDSA)

pid_file = "/tmp/vault-agent.pid"
log_level = "info"

vault {
  address = "http://vault:8200"
  retry {
    num_retries = 5
  }
}

auto_auth {
  method {
    type = "approle"
    config = {
      role_id_file_path = "/vault/secrets/role-id"
      secret_id_file_path = "/vault/secrets/secret-id"
      remove_secret_id_file_after_reading = false
    }
  }

  # Sink for the API token (consumed by tesa-api at /vault/token/api-token).
  # SECURITY: the sink lives on a host bind-mount, so it must NOT be
  # world-readable (0644 would expose a live Vault token to any host user).
  # The file sink has no owner option and rewrites the file on every re-auth,
  # so run-agent-with-autorotate.sh re-asserts owner uid 1000 (the api user)
  # + mode 0440 in a short loop after each render.
  sink {
    type = "file"
    config = {
      path = "/vault/token/api-token"
      mode = 0640
    }
  }
}

# ==============================================================================
# Template 1: API Token Info (for monitoring / debugging)
# ==============================================================================
template {
  contents = <<-EOF
  {{ with secret "auth/token/lookup-self" }}
  {
    "token_ttl": {{ .Data.ttl }},
    "token_policies": {{ .Data.policies | toJSON }},
    "token_expire_time": "{{ .Data.expire_time }}",
    "last_renewal": "{{ timestamp }}"
  }
  {{ end }}
  EOF
  destination = "/vault/token/api-token-info.json"
  # Same host bind-mount rationale as the token sink: not world-readable.
  perms = "0640"
}

# ==============================================================================
# Template 2: EMQX RSA Certificate Bundle (single issuance -> split script)
# ==============================================================================
template {
  source      = "/vault/templates/emqx-bundle.ctmpl"
  destination = "/opt/emqx/etc/certs/emqx-bundle.pem"
  perms       = "0600"
  command     = "/bin/sh /vault/scripts/split-emqx-bundle.sh"
}

# ==============================================================================
# Template 3: EMQX ECDSA Certificate Bundle (dual-cert support)
# ==============================================================================
# Issues an ECDSA (P-256) cert alongside the RSA cert above. The split script
# emits cert-with-chain.pem / key.pem / vault-ca-bundle.pem referenced by
# emqx.conf ssl_options.
template {
  source      = "/vault/templates/emqx-ecdsa-bundle.ctmpl"
  destination = "/opt/emqx/etc/certs/emqx-ecdsa-bundle.pem"
  perms       = "0600"
  command     = "/bin/sh /vault/scripts/split-emqx-bundle.sh"
}

# ==============================================================================
# Cache and listener
# ==============================================================================
cache {
  use_auto_auth_token = true
}

listener "tcp" {
  address = "0.0.0.0:8100"
  tls_disable = true
}
