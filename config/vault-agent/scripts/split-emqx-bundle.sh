#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# TESAIoT Community Edition
# Split a combined EMQX bundle (cert+key+issuing CA+root CA) into
# cert-with-chain.pem, key.pem, and vault-ca-bundle.pem
set -eu

BUNDLE="/opt/emqx/etc/certs/emqx-bundle.pem"
CERT_OUT="/opt/emqx/etc/certs/cert-with-chain.pem"
KEY_OUT="/opt/emqx/etc/certs/key.pem"
CA_OUT="/opt/emqx/etc/certs/vault-ca-bundle.pem"

if [ ! -f "$BUNDLE" ]; then
  echo "[split] bundle not found: $BUNDLE" >&2
  exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Extract leaf cert block between markers
awk '/^##### BEGIN EMQX CERTIFICATE #####/{flag=1;next}/^##### END EMQX CERTIFICATE #####/{flag=0}flag' "$BUNDLE" > "$TMPDIR/leaf.pem"

# Extract key block
awk '/^##### BEGIN EMQX PRIVATE KEY #####/{flag=1;next}/^##### END EMQX PRIVATE KEY #####/{flag=0}flag' "$BUNDLE" > "$TMPDIR/key.pem"

# Extract issuing CA
awk '/^##### BEGIN ISSUING CA #####/{flag=1;next}/^##### END ISSUING CA #####/{flag=0}flag' "$BUNDLE" > "$TMPDIR/issuing_ca.pem"

# Extract root CA
awk '/^##### BEGIN ROOT CA #####/{flag=1;next}/^##### END ROOT CA #####/{flag=0}flag' "$BUNDLE" > "$TMPDIR/root_ca.pem"

# Quick validation BEFORE writing: the hashicorp/vault image has no openssl,
# so validate structurally (non-empty + PEM markers) with grep instead.
pem_ok() {  # file
  [ -s "$1" ] && grep -q -- "-----BEGIN" "$1"
}
pem_ok "$TMPDIR/leaf.pem"        || { echo "[split] invalid/empty server cert in bundle" >&2; exit 1; }
pem_ok "$TMPDIR/key.pem"         || { echo "[split] invalid/empty private key in bundle" >&2; exit 1; }
pem_ok "$TMPDIR/issuing_ca.pem"  || { echo "[split] invalid/empty issuing CA in bundle" >&2; exit 1; }

# Write outputs. SECURITY/OWNERSHIP: the emqx image runs as uid/gid 1000, so
# the private key MUST be readable by 1000 (0640 root:root would make every
# TLS listener fail to start on a fresh install). This script runs as root
# inside the vault-agent container, so chown works on the shared volume.
cat "$TMPDIR/leaf.pem" "$TMPDIR/issuing_ca.pem" > "$CERT_OUT"
chown 1000:1000 "$CERT_OUT"
chmod 0644 "$CERT_OUT"

cp "$TMPDIR/key.pem" "$KEY_OUT"
chown 1000:1000 "$KEY_OUT"
chmod 0600 "$KEY_OUT"

cat "$TMPDIR/issuing_ca.pem" "$TMPDIR/root_ca.pem" > "$CA_OUT"
chown 1000:1000 "$CA_OUT"
chmod 0644 "$CA_OUT"

# Print summary
echo "[split] Wrote:"
echo "  - $CERT_OUT"
echo "  - $KEY_OUT"
echo "  - $CA_OUT"

# Split ECDSA bundle if present
ECDSA_BUNDLE="/opt/emqx/etc/certs/emqx-ecdsa-bundle.pem"
ECDSA_CERT_OUT="/opt/emqx/etc/certs/ecdsa-cert-with-chain.pem"
ECDSA_KEY_OUT="/opt/emqx/etc/certs/ecdsa-key.pem"

if [ -f "$ECDSA_BUNDLE" ]; then
  echo "[split] Found ECDSA bundle, splitting..."
  awk '/^##### BEGIN ECDSA CERTIFICATE #####/{flag=1;next}/^##### END ECDSA CERTIFICATE #####/{flag=0}flag' "$ECDSA_BUNDLE" > "$TMPDIR/ecdsa_leaf.pem"
  awk '/^##### BEGIN ECDSA PRIVATE KEY #####/{flag=1;next}/^##### END ECDSA PRIVATE KEY #####/{flag=0}flag' "$ECDSA_BUNDLE" > "$TMPDIR/ecdsa_key.pem"
  awk '/^##### BEGIN ISSUING CA #####/{flag=1;next}/^##### END ISSUING CA #####/{flag=0}flag' "$ECDSA_BUNDLE" > "$TMPDIR/ecdsa_issuing_ca.pem"

  pem_ok "$TMPDIR/ecdsa_leaf.pem" || { echo "[split] invalid/empty ECDSA cert in bundle" >&2; }

  # Same ownership rationale as the RSA outputs above: emqx runs as uid 1000.
  cat "$TMPDIR/ecdsa_leaf.pem" "$TMPDIR/ecdsa_issuing_ca.pem" > "$ECDSA_CERT_OUT"
  chown 1000:1000 "$ECDSA_CERT_OUT"
  chmod 0644 "$ECDSA_CERT_OUT"

  cp "$TMPDIR/ecdsa_key.pem" "$ECDSA_KEY_OUT"
  chown 1000:1000 "$ECDSA_KEY_OUT"
  chmod 0600 "$ECDSA_KEY_OUT"

  echo "[split] Wrote ECDSA:"
  echo "  - $ECDSA_CERT_OUT"
  echo "  - $ECDSA_KEY_OUT"
fi

# Attempt EMQX reload if available in PATH (inside agent container we may not reach EMQX)
if command -v emqx >/dev/null 2>&1; then
  emqx ctl reload || true
fi

exit 0

