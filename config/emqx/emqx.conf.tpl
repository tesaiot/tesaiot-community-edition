# SPDX-License-Identifier: Apache-2.0
# Copyright (c) TESAIoT Platform contributors
#
# TESAIoT Community Edition - EMQX MQTT Broker Configuration (single-org)
# ====================================================================
# Provides three device-facing transports:
#   - plain TCP (1883)      : local/dev only
#   - mTLS (8883)           : mutual TLS, client certificate required (Vault PKI)
#   - serverTLS (8884)      : server TLS only, username/password over TLS
# Authentication and authorization are delegated to the CE API webhooks
# (built-in DB is used only for the internal mqtt-bridge service account).

node {
  # Stable hostname to avoid random container-id hostnames
  name = "emqx@tesa-emqx"
  # Cluster cookie - override via EMQX_NODE__COOKIE env (do not ship a real secret)
  cookie = "CHANGEME_EMQX_COOKIE"
  data_dir = "/opt/emqx/data"
}

cluster {
  name = tesaiot
  discovery_strategy = manual
}

dashboard {
  listeners.http {
    bind = "0.0.0.0:18083"
  }
  default_username = "admin"
  # Override via EMQX_DASHBOARD__DEFAULT_PASSWORD env (do not ship a real secret)
  default_password = "CHANGEME_DASHBOARD_PASSWORD"
}

## ========================================
## AUTHENTICATION CHAIN (Order Matters!)
## ========================================
## Chain: 1. Built-in DB (internal mqtt-bridge) -> 2. HTTP webhook (devices/users)
## If the first authenticator returns "ignore", the next one is tried.
## This keeps the internal bridge working even while the API is restarting.
authentication = [
  ## FIRST: Built-in database for the internal mqtt-bridge service account.
  ## Bootstrapped from auth-built-in-db-bootstrap.csv. Always available.
  {
    mechanism = password_based
    backend = built_in_database
    enable = true
    user_id_type = username
    password_hash_algorithm {
      name = plain   ## internal service account only
      salt_position = disable
    }
  },
  ## SECOND: HTTP webhook for IoT devices and users.
  ## The CE API verifies password_hash (serverTLS) or client-cert CN
  ## against the MongoDB device registry + Vault PKI serial (mTLS).
  {
    mechanism = password_based
    backend = http
    enable = true
    method = post
    url = "http://tesa-api:5566/api/v1/emqx/auth"
    headers {
      "content-type" = "application/json"
      ## Shared secret - override via EMQX_WEBHOOK_SECRET / api EMQX_WEBHOOK_SECRET
      "authorization" = "Bearer CHANGEME_WEBHOOK_SECRET"
    }
    body {
      username = "${username}"
      password = "${password}"
      clientid = "${clientid}"
      peerhost = "${peerhost}"
      protocol = "${protocol}"
      sockport = "${sockport}"
      cert_common_name = "${cert_common_name}"
      cert_subject = "${cert_subject}"
    }
  }
]

authorization {
  sources = [
    {
      type = http
      enable = true
      method = post
      url = "http://tesa-api:5566/api/v1/emqx/acl"
      headers {
        content-type = "application/json"
        ## Shared secret - must match the API's EMQX_WEBHOOK_SECRET
        authorization = "Bearer CHANGEME_WEBHOOK_SECRET"
      }
      body {
        username = "${username}"
        topic = "${topic}"
        action = "${action}"
        clientid = "${clientid}"
        protocol = "${protocol}"
        sockport = "${sockport}"
      }
    }
  ]
  no_match = deny
  deny_action = disconnect
  cache {
    enable = true
    max_size = 10000
    ttl = 1m
  }
}

## Plain TCP MQTT listener (non-encrypted).
## SECURITY: the internal mqtt-bridge connects to the serverTLS listener
## (tesa-emqx:8884, MQTT_USE_TLS=true, CA = the vault-agent-rendered
## vault-ca-bundle.pem) - NOT to this plaintext listener. 1883 is kept enabled
## only as a local/dev convenience and is NOT exposed to the LAN:
## docker-compose.yml publishes it on 127.0.0.1 only (loopback). For an
## all-TLS deployment set `enable = false` here to switch it off entirely.
listeners.tcp.default {
  bind = "0.0.0.0:1883"
  max_connections = 1024000
}

## WebSocket listener (non-encrypted). Loopback-published only (see compose).
listeners.ws.default {
  bind = "0.0.0.0:8083"
  max_connections = 1024000
}

## mTLS listener (8883) - mutual TLS with client certificates.
## Devices must present a Vault-PKI-issued client certificate.
## Server cert/key/CA are rendered by the Vault Agent into /opt/emqx/etc/certs.
##
## REVOCATION ENFORCEMENT (fail-closed):
##   enable_crl_check makes EMQX fetch the CRL Distribution Point embedded in
##   each client certificate (Vault sets this to
##   http://tesa-vault:8200/v1/pki-int/crl on every device cert) during the TLS
##   handshake and REJECT the connection if the presented cert's serial is on
##   the CRL. Revoking a cert via the API calls pki-int/revoke + crl/rotate, so
##   the serial appears on that CRL and the device can no longer connect once
##   the CRL cache refreshes (see crl_cache.refresh_interval below).
listeners.ssl.mtls {
  bind = "0.0.0.0:8883"
  max_connections = 1024000
  ssl_options {
    keyfile = "/opt/emqx/etc/certs/key.pem"
    certfile = "/opt/emqx/etc/certs/cert-with-chain.pem"
    cacertfile = "/opt/emqx/etc/certs/vault-ca-bundle.pem"
    verify = "verify_peer"
    fail_if_no_peer_cert = true
    ## Enforce certificate revocation via the CRL Distribution Point that Vault
    ## PKI embeds in every issued device certificate. A revoked serial is
    ## rejected at the TLS handshake (before the auth webhook is even called).
    ## EMQX caches each fetched CRL and refreshes it every 15 minutes by default,
    ## so a freshly revoked device stops connecting within that window. (Cache
    ## tuning is a global EMQX setting; the documented per-listener key here is
    ## enable_crl_check.)
    enable_crl_check = true
    ## NOTE: partial_chain must stay disabled when enable_crl_check is on so the
    ## full chain (incl. the issuing CA that signed the CRL) is validated.
    versions = ["tlsv1.2", "tlsv1.3"]
    secure_renegotiate = true
    reuse_sessions = true
    honor_cipher_order = true
    depth = 10
    ciphers = [
      "TLS_AES_256_GCM_SHA384",
      "TLS_AES_128_GCM_SHA256",
      "TLS_CHACHA20_POLY1305_SHA256",
      "ECDHE-RSA-AES256-GCM-SHA384",
      "ECDHE-RSA-AES128-GCM-SHA256",
      "ECDHE-ECDSA-AES256-GCM-SHA384",
      "ECDHE-ECDSA-AES128-GCM-SHA256",
      "ECDHE-RSA-AES256-SHA384",
      "ECDHE-RSA-AES128-SHA256"
    ]
  }
}

## serverTLS listener (8884) - server TLS only, username/password auth over TLS.
## No client certificate is required (verify_none).
listeners.ssl.servertls {
  bind = "0.0.0.0:8884"
  max_connections = 1024000
  ssl_options {
    keyfile = "/opt/emqx/etc/certs/key.pem"
    certfile = "/opt/emqx/etc/certs/cert-with-chain.pem"
    cacertfile = "/opt/emqx/etc/certs/vault-ca-bundle.pem"
    verify = "verify_none"
    fail_if_no_peer_cert = false
    versions = ["tlsv1.2", "tlsv1.3"]
    ciphers = [
      "TLS_AES_256_GCM_SHA384",
      "TLS_AES_128_GCM_SHA256",
      "TLS_CHACHA20_POLY1305_SHA256",
      "ECDHE-RSA-AES256-GCM-SHA384",
      "ECDHE-RSA-AES128-GCM-SHA256",
      "ECDHE-RSA-CHACHA20-POLY1305",
      "ECDHE-ECDSA-AES256-GCM-SHA384",
      "ECDHE-ECDSA-AES128-GCM-SHA256",
      "ECDHE-ECDSA-CHACHA20-POLY1305",
      "DHE-RSA-AES256-GCM-SHA384",
      "DHE-RSA-AES128-GCM-SHA256",
      "AES256-GCM-SHA384",
      "AES128-GCM-SHA256"
    ]
  }
}

## WebSocket-over-TLS listener (server TLS only).
listeners.wss.default {
  bind = "0.0.0.0:8084"
  max_connections = 1024000
  ssl_options {
    keyfile = "/opt/emqx/etc/certs/key.pem"
    certfile = "/opt/emqx/etc/certs/cert-with-chain.pem"
    cacertfile = "/opt/emqx/etc/certs/vault-ca-bundle.pem"
    verify = "verify_none"
    fail_if_no_peer_cert = false
  }
}

## Disable the default SSL listener to avoid port conflicts.
listeners.ssl.default {
  enable = false
}

## MQTT protocol configuration.
mqtt {
  max_packet_size = 10MB
  max_qos_allowed = 2
  retain_available = true
  wildcard_subscription = true
  shared_subscription = true
  max_subscriptions = infinity
  max_inflight = 32
  max_awaiting_rel = 100
  await_rel_timeout = 300s
  session_expiry_interval = 2h
  max_mqueue_len = 1000
  idle_timeout = 60s
}

## Logging configuration.
log {
  file {
    enable = true
    path = "/opt/emqx/log/emqx.log"
    level = warning
    rotation_size = 50MB
    rotation_count = 10
  }
  console {
    enable = true
    level = warning
  }
}
