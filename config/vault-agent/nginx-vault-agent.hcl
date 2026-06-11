# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent configuration for nginx
#
# Renders the serverTLS cert/key and the client-CA bundle used for mTLS
# termination at the nginx edge.

pid_file = "/tmp/vault-agent-nginx.pid"
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
    config {
      role_id_file_path = "/vault/secrets/role-id"
      secret_id_file_path = "/vault/secrets/secret-id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink {
    type = "file"
    config {
      path = "/tmp/vault-token-nginx"
    }
  }
}

# Server certificate (full chain)
template {
  source      = "/vault/templates/nginx-cert.ctmpl"
  destination = "/etc/nginx/ssl/fullchain.pem"
  perms       = "0644"
  command     = "echo 'Certificate renewed for nginx'"
}

# Private key
template {
  source      = "/vault/templates/nginx-key.ctmpl"
  destination = "/etc/nginx/ssl/privkey.pem"
  perms       = "0600"
  command     = "echo 'Private key renewed for nginx'"
}

# CA certificate (client-CA bundle for mTLS verification)
template {
  source      = "/vault/templates/nginx-ca.ctmpl"
  destination = "/etc/nginx/ssl/ca.crt"
  perms       = "0644"
}
