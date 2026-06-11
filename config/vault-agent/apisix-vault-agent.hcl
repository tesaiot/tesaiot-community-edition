# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent configuration for APISIX

pid_file = "/tmp/vault-agent-apisix.pid"
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

  sink {
    type = "file"
    config = {
      path = "/tmp/vault-token-apisix"
    }
  }
}

# Server certificate for APISIX (serverTLS / mTLS on 9443)
template {
  source      = "/vault/templates/apisix-cert.ctmpl"
  destination = "/usr/local/apisix/conf/cert/server.crt"
  perms       = "0644"
}

template {
  source      = "/vault/templates/apisix-key.ctmpl"
  destination = "/usr/local/apisix/conf/cert/server.key"
  perms       = "0600"
  command     = "echo 'Certificate renewed for APISIX'"
}

template {
  source      = "/vault/templates/ca.ctmpl"
  destination = "/usr/local/apisix/conf/cert/ca.crt"
  perms       = "0644"
}
