#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition - device certificate renewal hook
#
# Invoked by the Vault Agent when a device certificate is re-rendered.
# Core flow: validate new cert -> notify the API -> copy into the app dir.

set -e

CERT_DIR="${CERT_DIR:-/vault/certificates}"
LOG_FILE="${LOG_FILE:-/var/log/vault-agent-renewal.log}"
DEVICE_ID="${DEVICE_ID:-unknown}"
API_ENDPOINT="${API_ENDPOINT:-http://tesa-api:5566}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || echo "$1"
}

log "Certificate renewal triggered for device: $DEVICE_ID"

# Verify new certificates exist
if [ ! -f "$CERT_DIR/device-cert.pem" ] || [ ! -f "$CERT_DIR/device-key.pem" ]; then
    log "ERROR: Certificate files not found after renewal"
    exit 1
fi

# Extract certificate metadata
CERT_SERIAL=$(openssl x509 -in "$CERT_DIR/device-cert.pem" -serial -noout | cut -d'=' -f2)
CERT_EXPIRY=$(openssl x509 -in "$CERT_DIR/device-cert.pem" -enddate -noout | cut -d'=' -f2)

log "New certificate serial: $CERT_SERIAL"
log "New certificate expiry: $CERT_EXPIRY"

# Notify the API about the renewal
if command -v curl >/dev/null 2>&1; then
    curl -X POST "$API_ENDPOINT/api/v1/devices/$DEVICE_ID/certificate-renewed" \
        -H "Content-Type: application/json" \
        -H "X-Device-ID: $DEVICE_ID" \
        -d "{
            \"serial_number\": \"$CERT_SERIAL\",
            \"expiry_date\": \"$CERT_EXPIRY\",
            \"renewed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }" || log "WARNING: Failed to notify API about renewal"
fi

# Copy certificates into the application directory if it exists
if [ -d "/app/certs" ]; then
    cp "$CERT_DIR/device-cert.pem" "/app/certs/"
    cp "$CERT_DIR/device-key.pem" "/app/certs/"
    [ -f "$CERT_DIR/ca-chain.pem" ] && cp "$CERT_DIR/ca-chain.pem" "/app/certs/"
    chmod 644 "/app/certs/device-cert.pem"
    chmod 600 "/app/certs/device-key.pem"
    [ -f "/app/certs/ca-chain.pem" ] && chmod 644 "/app/certs/ca-chain.pem"
    log "Certificates copied to application directory"
fi

log "Certificate renewal completed successfully"
exit 0
