ui = true
disable_mlock = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "https://0.0.0.0:8201"

# Development mode settings
log_level = "INFO"
log_format = "json"

# Simple lease configuration for development
default_lease_ttl = "168h"
max_lease_ttl = "8760h"

# Telemetry disabled for development
telemetry {
  disable_hostname = true
}

# Cluster configuration for single-node development
cluster_name = "tesa-vault-dev-cluster"

# Plugin directory
plugin_directory = "/vault/plugins"