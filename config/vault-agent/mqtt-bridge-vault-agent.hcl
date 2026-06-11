# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - Vault Agent configuration for the MQTT telemetry bridge
#
# Optional: only needed when the bridge connects to EMQX over TLS/mTLS
# (MQTT_USE_TLS=true). For the default plain-TCP path this agent is unused.

pid_file = "/tmp/vault-agent-mqtt-bridge.pid"
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
      path = "/tmp/vault-token-mqtt-bridge"
    }
  }
}

# Client certificate for the bridge (mTLS to EMQX)
template {
  source      = "/vault/templates/mqtt-bridge-cert.ctmpl"
  destination = "/vault/certs/server.crt"
  perms       = "0644"
  command     = "pkill -SIGHUP -f mqtt_telemetry_bridge.py || true"
}

# Private key
template {
  source      = "/vault/templates/mqtt-bridge-key.ctmpl"
  destination = "/vault/certs/server.key"
  perms       = "0600"
  command     = "pkill -SIGHUP -f mqtt_telemetry_bridge.py || true"
}

# CA certificate
template {
  source      = "/vault/templates/ca.ctmpl"
  destination = "/vault/certs/ca.crt"
  perms       = "0644"
}
