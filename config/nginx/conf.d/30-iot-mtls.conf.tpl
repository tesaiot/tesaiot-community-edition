# TESAIoT Community Edition
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Dedicated IoT device endpoint with mutual TLS (mTLS).
# Devices present a client certificate issued by the Vault PKI; nginx verifies
# it against the client CA bundle and forwards the verification result + the
# certificate to the API, which performs per-device authorization.
#
# SECURITY MODEL (NON-SPOOFABLE mTLS)
#   This server block REQUIRES a valid client certificate (ssl_verify_client on).
#   nginx terminates TLS, verifies the client cert against the Vault PKI CA
#   bundle, and is the ONLY component that emits the X-Client-* headers, derived
#   from its trusted $ssl_client_* variables. Any X-Client-* header supplied by a
#   client is unconditionally overwritten below, so a caller cannot forge a
#   device identity. The API (require_api_key_or_mtls) trusts these headers ONLY
#   when X-Client-Verify == 'SUCCESS'.
#
# MODE SELECTION
#   mTLS (this block): ssl_verify_client on -> reject any client without a
#       certificate that chains to the configured CA bundle. FAIL CLOSED.
#   serverTLS-only endpoints must live in a SEPARATE server block that does NOT
#       set any X-Client-* headers (so they can never assert device identity).
#
# Certificates (see README.md):
#   /etc/nginx/certs/server-cert.pem   server certificate (+ chain)
#   /etc/nginx/certs/server-key.pem    server private key
#   /etc/nginx/certs/ca-bundle.pem     client CA bundle (Vault PKI issuing CA chain)

server {
    listen 9444 ssl;
    server_name _;

    # ---- serverTLS ----
    ssl_certificate     /etc/nginx/certs/server-cert.pem;
    ssl_certificate_key /etc/nginx/certs/server-key.pem;

    ssl_protocols       TLSv1.2 TLSv1.3;
    # Explicit modern AEAD-only suite list (no CBC / SHA-1) - same set as
    # config/apisix/config.yaml. TLS 1.3 suites are unaffected by ssl_ciphers.
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;
    ssl_ecdh_curve      prime256v1:secp384r1;
    # Session tickets would let a recorded ticket resume a session without
    # forward secrecy of the ticket key; disable (resumption via session cache).
    ssl_session_tickets off;

    # ---- Security headers ----
    # NOTE (nginx add_header inheritance is replace-not-merge): these only
    # apply to locations that declare NO add_header of their own. Every
    # location below relies on inheritance (fixed-response locations use
    # default_type instead of add_header Content-Type) so these headers are
    # emitted on EVERY response from this server block.
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;

    # ---- mTLS (client certificate verification) ----
    # REQUIRE a client certificate that chains to the Vault PKI CA bundle.
    # "on" => nginx aborts the TLS handshake for any client that does not
    # present a certificate verifiable against ca-bundle.pem (FAIL CLOSED).
    ssl_client_certificate /etc/nginx/certs/ca-bundle.pem;
    ssl_verify_client      on;
    ssl_verify_depth       2;

    # ---- Anti-spoofing: neutralise any client-supplied X-Client-* headers ----
    # These headers MUST originate from nginx ($ssl_client_*) only. Clearing
    # them at server scope guarantees that even if a request omits an explicit
    # per-location proxy_set_header, no forged inbound value can survive.
    proxy_set_header X-Client-Cert        "";
    proxy_set_header X-Client-Verify      "";
    proxy_set_header X-Client-S-DN        "";
    proxy_set_header X-Client-I-DN        "";
    proxy_set_header X-Client-Serial      "";
    proxy_set_header X-Client-Fingerprint "";
    # Also clear any inbound gateway marker; it is (re)asserted per-location
    # below ONLY after the client cert has been verified by nginx.
    proxy_set_header X-MTLS-Gateway       "";

    # IoT telemetry ingest (generic)
    # No CORS headers here on purpose: this is a machine-to-machine mTLS
    # ingest path (devices present client certs); browsers never call it, and
    # 'Access-Control-Allow-Origin: *' on an authenticated endpoint is a
    # needless relaxation. Browser/WS ingest, if ever needed, belongs on a
    # separate serverTLS endpoint with a scoped origin.
    location /api/v1/telemetry {
        set $api_upstream tesa-api:5566;
        proxy_pass http://$api_upstream/api/v1/telemetry;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Forward mTLS client-cert details to the API for device auth
        proxy_set_header X-Client-Cert        $ssl_client_escaped_cert;
        proxy_set_header X-Client-Verify      $ssl_client_verify;
        proxy_set_header X-Client-S-DN        $ssl_client_s_dn;
        proxy_set_header X-Client-I-DN        $ssl_client_i_dn;
        proxy_set_header X-Client-Serial      $ssl_client_serial;
        proxy_set_header X-Client-Fingerprint $ssl_client_fingerprint;
        # Defence-in-depth marker proving this request traversed the verified
        # mTLS terminator. auth.py requires it (== MTLS_GATEWAY_SECRET) before
        # honouring any X-Client-* header. Injected from .env by
        # generate-secrets.sh (replaces the placeholder below).
        proxy_set_header X-MTLS-Gateway       "CHANGEME_MTLS_GATEWAY_SECRET";

        proxy_connect_timeout 10s;
        proxy_send_timeout    10s;
        proxy_read_timeout    10s;
    }

    # Per-device telemetry ingest (M2M mTLS path - no CORS, see above)
    location ~ ^/api/v1/devices/([^/]+)/telemetry$ {
        set $api_upstream tesa-api:5566;
        proxy_pass http://$api_upstream$request_uri;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Device-ID       $1;

        proxy_set_header X-Client-Cert        $ssl_client_escaped_cert;
        proxy_set_header X-Client-Verify      $ssl_client_verify;
        proxy_set_header X-Client-S-DN        $ssl_client_s_dn;
        proxy_set_header X-Client-I-DN        $ssl_client_i_dn;
        proxy_set_header X-Client-Serial      $ssl_client_serial;
        proxy_set_header X-Client-Fingerprint $ssl_client_fingerprint;
        # Defence-in-depth marker (see generic telemetry location above).
        proxy_set_header X-MTLS-Gateway       "CHANGEME_MTLS_GATEWAY_SECRET";

        proxy_connect_timeout 10s;
        proxy_send_timeout    10s;
        proxy_read_timeout    10s;
    }

    # Health check (default_type, NOT add_header Content-Type: a location-
    # level add_header would suppress the inherited security headers above)
    location /health {
        access_log off;
        default_type text/plain;
        return 200 "healthy\n";
    }

    location / {
        default_type application/json;
        return 404 '{"error": "Endpoint not found"}';
    }
}
