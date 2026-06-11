# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# APISIX declarative resources (CE, single-organization).
# Loaded at boot by standalone YAML mode (see config.yaml). Holds the server
# TLS material (serverTLS mode), routes, and example device-key consumers.

# --------------------------------------------------------------------------
# Server TLS certificate (serverTLS mode).
# Replace the PLACEHOLDER cert/key with a Vault-PKI-issued server certificate
# (e.g. emit pki-int/issue/platform-service into ./config/tls and paste here,
# or provision at runtime via the Admin API). NEVER commit a real private key.
# For mTLS mode, add a `client` block with `ca` + `depth` and set
# `verify_client: true` (see README).
# --------------------------------------------------------------------------
ssls:
  - id: 1
    snis:
      - "localhost"
      - "tesa.iot"
    cert: |
      -----BEGIN CERTIFICATE-----
      CHANGEME_REPLACE_WITH_VAULT_PKI_SERVER_CERTIFICATE
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      CHANGEME_REPLACE_WITH_VAULT_PKI_SERVER_PRIVATE_KEY
      -----END PRIVATE KEY-----

routes:
  # ----------------------------------------------------------------------
  # IoT device telemetry ingest (API-key auth via X-API-Key / ?api_key=)
  # ----------------------------------------------------------------------
  - id: "device-telemetry-ip"
    uri: "/api/v1/telemetry"
    methods: ["POST", "OPTIONS"]
    upstream:
      nodes:
        "tesa-api:5566": 1
      type: roundrobin
      pass_host: pass
    plugins:
      key-auth:
        header: "X-API-Key"
        query: "api_key"
        hide_credentials: true
      limit-req:
        rate: 1000
        burst: 2000
        key: "consumer_name"
        rejected_code: 429
        rejected_msg: "Rate limit exceeded"
      cors:
        allow_origin: "*"
        allow_methods: "POST,OPTIONS"
        allow_headers: "X-API-Key,Content-Type,Authorization"
        allow_credentials: false
        max_age: 5
      # Anti-spoofing: APISIX performs NO client-cert verification, so it must
      # never be able to assert a device's mTLS identity. Strip every device-
      # auth header (and the mTLS gateway marker) before proxying to tesa-api,
      # so a forged "X-Client-Verify: SUCCESS" through this gateway is dropped.
      # Device mTLS is honoured ONLY via nginx 30-iot-mtls.conf.
      proxy-rewrite:
        headers:
          set:
            X-Powered-By: "APISIX"
          remove:
            - "X-Client-Cert"
            - "X-Client-Verify"
            - "X-Client-S-DN"
            - "X-Client-I-DN"
            - "X-Client-Serial"
            - "X-Client-Fingerprint"
            - "X-MTLS-Gateway"

  # Device-scoped telemetry: /api/v1/devices/<id>/telemetry
  - id: "device-telemetry-device-id"
    uri: "/api/v1/devices/*/telemetry"
    methods: ["POST", "OPTIONS"]
    upstream:
      nodes:
        "tesa-api:5566": 1
      type: roundrobin
      pass_host: pass
    plugins:
      key-auth:
        header: "X-API-Key"
        query: "api_key"
        hide_credentials: true
      limit-req:
        rate: 1000
        burst: 2000
        key: "consumer_name"
        rejected_code: 429
      # Anti-spoofing: strip device-auth headers (see device-telemetry-ip).
      proxy-rewrite:
        headers:
          set:
            X-Device-Route: "device-specific"
          remove:
            - "X-Client-Cert"
            - "X-Client-Verify"
            - "X-Client-S-DN"
            - "X-Client-I-DN"
            - "X-Client-Serial"
            - "X-Client-Fingerprint"
            - "X-MTLS-Gateway"

  # ----------------------------------------------------------------------
  # General API backend -> CE tesa-api (auth, users, devices, certs...)
  # ----------------------------------------------------------------------
  - id: "api-backend"
    uri: "/api/*"
    upstream:
      nodes:
        "tesa-api:5566": 1
      type: roundrobin
      pass_host: pass
    plugins:
      # Anti-spoofing: this catch-all /api/* route reaches the mTLS-gated
      # telemetry endpoints too. APISIX does not verify client certs, so strip
      # every device-auth header (and the gateway marker) so it can never
      # assert a device identity. (see device-telemetry-ip for rationale)
      proxy-rewrite:
        headers:
          remove:
            - "X-Client-Cert"
            - "X-Client-Verify"
            - "X-Client-S-DN"
            - "X-Client-I-DN"
            - "X-Client-Serial"
            - "X-Client-Fingerprint"
            - "X-MTLS-Gateway"

  # ----------------------------------------------------------------------
  # Admin / Telemetry Dashboard UI (single-page app, served by nginx)
  # ----------------------------------------------------------------------
  - id: "admin-ui"
    uri: "/*"
    upstream:
      nodes:
        # The admin-ui container's non-root nginx listens on 8080 (not 80).
        "tesa-admin-ui:8080": 1
      type: roundrobin
      pass_host: pass

# --------------------------------------------------------------------------
# Static device API-key consumer (single sample for the default org).
# ROTATE the key before use.
#
# In standalone YAML mode (this CE) consumers are static -- declared here and
# loaded at boot. There is NO dynamic per-device consumer registration: the
# Admin API does not mutate runtime state and this file is mounted read-only.
# Real device API keys are issued and validated by the API backend
# (api_key_service.py), not as APISIX consumers. The telemetry-route limit-req
# above is therefore a route-level (shared) limit, not a per-device quota.
# See config/apisix/README.md ("Rate limiting") for the honest description.
# --------------------------------------------------------------------------
consumers:
  - username: "device_sample"
    plugins:
      key-auth:
        key: "CHANGEME_DEVICE_API_KEY_SAMPLE"
      limit-req:
        rate: 1000
        burst: 2000
        key: "consumer_name"
#END
