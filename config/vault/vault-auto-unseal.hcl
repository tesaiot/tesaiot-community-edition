ui = true
disable_mlock = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  # Vault binds 0.0.0.0 INSIDE the container so in-cluster consumers can reach
  # it via the Docker DNS name tesa-vault:8200 on the backend (tesa-internal)
  # network. The container is NOT attached to the LAN-reachable tesa-external
  # network and the host publish is loopback-only (127.0.0.1:8200), so this
  # listener is never exposed off-box (see docker-compose.yml `vault.ports`).
  address     = "0.0.0.0:8200"

  # SECURITY NOTE (TLS): tls_disable=1 is acceptable here ONLY because traffic
  # stays on the private container bridge + host loopback. To terminate TLS at
  # Vault itself, provision a server cert/key (e.g. rendered by the Vault Agent
  # from pki-int into /opt/vault/tls) and replace the two lines below with:
  #   tls_cert_file = "/opt/vault/tls/tls.crt"
  #   tls_key_file  = "/opt/vault/tls/tls.key"
  # then flip api_addr/cluster_addr to https and rewire consumers (VAULT_ADDR,
  # vault-agent.hcl, emqx CRL URL) to https://tesa-vault:8200. This requires CA
  # wiring on every consumer, so it is left as a documented opt-in.
  tls_disable = 1
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "https://0.0.0.0:8201"

# Logging
log_level = "INFO"
log_format = "json"

# Seal configuration with Shamir's secret sharing
# For production, consider migrating to cloud KMS auto-unseal
default_lease_ttl = "168h"
max_lease_ttl = "8760h"

# Auto-unseal configuration (placeholder for future cloud KMS)
# When ready to migrate to cloud auto-unseal, uncomment and configure:
# seal "awskms" {
#   region     = "us-east-1"
#   kms_key_id = "your-kms-key-id"
# }

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

# Enterprise features (if available)
# license_path = "/vault/config/vault.hclic"

# Auto-reload configuration for updates
reload = true

# Additional security settings
default_max_request_duration = "90s"
max_request_size = "33554432"

# NOTE: `entropy "seal" { mode = "augmentation" }` and `license_path` are
# Vault Enterprise-only features and are intentionally omitted here so this
# config runs on the open-source hashicorp/vault image.