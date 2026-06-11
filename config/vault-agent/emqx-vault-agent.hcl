# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent configuration for EMQX (standalone variant)
#
# Standalone alternative to the unified vault-agent.hcl when running a
# dedicated agent for EMQX only.

pid_file = "/tmp/vault-agent-emqx.pid"
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
      path = "/tmp/vault-token-emqx"
    }
  }
}

# Certificate bundle for EMQX (single issuance, split into cert/key/ca by script)
template {
  source      = "/vault/templates/emqx-bundle.ctmpl"
  destination = "/opt/emqx/etc/certs/emqx-bundle.pem"
  perms       = "0600"
  command     = "/bin/sh /vault/scripts/split-emqx-bundle.sh"
}
