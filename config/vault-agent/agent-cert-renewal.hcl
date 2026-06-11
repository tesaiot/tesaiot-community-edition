# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent configuration for device certificate
# auto-renewal.
#
# Renews IoT device certificates from the intermediate CA before expiry,
# following enterprise PKI best practices. Optional: enable only when
# server-side device cert auto-renewal is wanted.

cache {
  use_auto_auth_token = true
}

vault {
  address = "http://vault:8200"
  retry {
    num_retries = 5
  }
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/vault/secrets/role-id"
      secret_id_file_path = "/vault/secrets/secret-id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/vault/token/agent-token"
      mode = 0640
    }
  }
}

# Device certificate (renewed when within ~30 days of expiry)
template {
  source = "/vault/templates/device-cert.tmpl"
  destination = "/vault/certificates/device-cert.pem"

  exec {
    command = ["/vault/scripts/cert-renewal.sh"]
    timeout = "30s"
  }
}

# Certificate chain
template {
  source = "/vault/templates/ca-chain.tmpl"
  destination = "/vault/certificates/ca-chain.pem"
}

# Private key (renewed with certificate)
template {
  source = "/vault/templates/device-key.tmpl"
  destination = "/vault/certificates/device-key.pem"
  perms = "0600"
}

listener "tcp" {
  address = "127.0.0.1:8200"
  tls_disable = true
}
