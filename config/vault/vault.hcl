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

# Logging
log_level = "INFO"
log_format = "json"

# Seal configuration (using default Shamir's secret sharing)
default_lease_ttl = "168h"
max_lease_ttl = "8760h"

# Telemetry (disabled for production security)
telemetry {
  disable_hostname = true
  prometheus_retention_time = "30s"
  statsd_address = ""
}

# Cluster configuration for single-node (can be extended for HA)
cluster_name = "tesa-vault-cluster"

# PKI tuning
raw_storage_endpoint = true
introspection_endpoint = true

# Plugin directory
plugin_directory = "/vault/plugins"