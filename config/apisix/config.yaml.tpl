# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# APISIX runtime configuration (CE, single-organization).
# Standalone YAML mode -- NO etcd required. Declarative resources
# (routes / ssls / consumers) are loaded from apisix.yaml at boot.

apisix:
  enable_ipv6: false
  node_listen: 9080
  # NOTE: APISIX runs in standalone YAML mode (deployment.config_provider: yaml,
  # APISIX_STAND_ALONE=true). In this mode the Admin API does NOT mutate runtime
  # state -- routes/ssls/consumers come only from apisix.yaml at boot, which is
  # mounted read-only. There is therefore no dynamic per-device consumer
  # registration in the CE; device API keys are issued/validated by the API
  # backend (api_key_service.py). The admin listener below is kept only for
  # read-only introspection; do not rely on it to create consumers.
  # VERIFIED 2026-06: the API's device_auth_service still probes/calls this
  # Admin API (APISIX_ADMIN_URL) when registering devices, so it stays
  # enabled; in standalone mode those writes are best-effort no-ops. The
  # compose publish is loopback-only (127.0.0.1:9180).
  enable_admin: true
  admin_listen:
    ip: 0.0.0.0
    port: 9180
  # The placeholder below is filled from .env (APISIX_ADMIN_KEY) when
  # generate-secrets.sh renders this template. In standalone mode it only
  # guards the (read-only) Admin API surface; it is NOT used to mint device
  # consumers (see note above and config/apisix/README.md).
  admin_key:
    - name: admin
      key: CHANGEME_APISIX_ADMIN_KEY
      role: admin
  ssl:
    ssl_ciphers: ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305
    ssl_protocols: TLSv1.2 TLSv1.3
    ssl_session_tickets: false
    listen:
      - port: 9443
        enable_http3: false
    enable: true
  proxy_mode: http
  router:
    ssl: radixtree_uri
    http: radixtree_uri
  # Optional MQTT TCP stream proxy in front of EMQX.
  # In the default CE topology devices connect to EMQX directly, so this is
  # commented out to avoid a host-port clash with EMQX. Uncomment to front MQTT
  # through APISIX (then expose 1884 in docker-compose and point devices at it).
  # stream_proxy:
  #   tcp:
  #     - 1884

deployment:
  role: data_plane
  role_data_plane:
    config_provider: yaml
    config_yaml: /usr/local/apisix/conf/apisix.yaml

# Plugin allowlist (HTTP)
plugins:
  - real-ip
  - proxy-rewrite
  - cors
  - ip-restriction
  - key-auth
  - jwt-auth
  - limit-count
  - limit-req
  - limit-conn
  - prometheus
  - http-logger
  - response-rewrite
  - client-control
  - request-validation

# Plugin allowlist (TCP/stream) -- used only if the MQTT stream proxy is enabled.
stream_plugins:
  - mqtt-proxy
  - ip-restriction
  - limit-conn

plugin_attr:
  mqtt-proxy:
    max_packet_size: 1048576
    client_id_pattern: "^[a-zA-Z0-9-_]+$"
