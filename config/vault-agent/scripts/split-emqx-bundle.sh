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

# Trust anchors that are NOT part of the Vault PKI belong in the CA bundle too.
# A device whose client certificate was issued by some other authority — an
# organisation's own device CA, or the factory certificate burned into an OPTIGA
# Trust M secure element by Infineon — can only be accepted by the mTLS listener
# if EMQX trusts that authority.
#
# This file is rewritten from the Vault bundle on every certificate renewal, so
# anything appended to it by hand disappears the next time the agent rotates the
# certificate. The failure is nasty: devices that worked for weeks start failing
# with `unknown_ca`, the broker itself still looks healthy, and the only clue is
# a TLS alert in its log. Anything dropped into trust-anchors.d survives every
# renewal instead.
#
#   docker cp my-device-ca.pem tesa-emqx:/opt/emqx/etc/certs/trust-anchors.d/
#
ANCHOR_DIR="/opt/emqx/etc/certs/trust-anchors.d"

# Create it even when empty, so the place to put an extra CA is discoverable on
# a running install instead of only being described in the docs. A failure here
# is not fatal — the bundle is still valid without any extra anchors.
if [ ! -d "$ANCHOR_DIR" ]; then
  if mkdir -p "$ANCHOR_DIR" 2>/dev/null; then
    chown 1000:1000 "$ANCHOR_DIR" 2>/dev/null || true
    chmod 0755 "$ANCHOR_DIR" 2>/dev/null || true
  else
    echo "[split] note: could not create $ANCHOR_DIR (extra trust anchors unsupported)" >&2
  fi
fi

if [ -d "$ANCHOR_DIR" ]; then
  for anchor in "$ANCHOR_DIR"/*.pem; do
    [ -f "$anchor" ] || continue
    if pem_ok "$anchor"; then
      cat "$anchor" >> "$CA_OUT"
      echo "[split] added trust anchor: $(basename "$anchor")"
    else
      # Appending a truncated file would corrupt the bundle and take down every
      # TLS listener, so skip it loudly rather than quietly.
      echo "[split] WARNING: skipping unreadable trust anchor $anchor" >&2
    fi
  done
fi

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

