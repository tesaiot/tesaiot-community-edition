# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from flask import Blueprint, request, jsonify, Response, g
from io import BytesIO
import os
import zipfile
from datetime import datetime
import json
import re
import requests

from ..core.auth import require_auth
from ..core.database import get_db

mqtt_quic_server_tls_bundle_bp = Blueprint('mqtt_quic_server_tls_bundle', __name__)

VAULT_ADDR = os.getenv('VAULT_ADDR', 'http://tesa-vault:8200')
PKI_INT = os.getenv('PKI_INT_MOUNT', 'pki-int')
PKI_ROOT = os.getenv('PKI_ROOT_MOUNT', 'pki-root')
VAULT_TOKEN = os.getenv('VAULT_TOKEN') or os.getenv('VAULT_ROOT_TOKEN')

# MQTT-QUIC configuration
MQTT_QUIC_HOST = os.getenv('TESA_PUBLIC_MQTT_HOST', 'localhost')
MQTT_QUIC_PORT = int(os.getenv('TESA_MQTT_QUIC_PORT', '14567'))


def _vault_headers():
    """Generate Vault authentication headers."""
    if not VAULT_TOKEN:
        return None
    return {'X-Vault-Token': VAULT_TOKEN}


def _normalize_pem_chain(text: str) -> str:
    """Normalize concatenated PEM certificates to have clean separators.

    - Extracts all CERTIFICATE blocks and rejoins with a blank line between.
    - Fixes cases where blocks are jammed together without newlines.
    - Returns trailing newline for good measure.
    """
    if not text:
        return ''
    try:
        blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", text, flags=re.DOTALL)
        if blocks:
            return "\n\n".join([b.strip() for b in blocks]) + "\n"
    except Exception:
        pass
    # If no blocks matched but content contains a PEM, return as-is
    return text if 'BEGIN CERTIFICATE' in text else ''


def _fetch_ca_chain_pems() -> str:
    """Return concatenated PEM (intermediate + root) from Vault or local files."""
    chain_pems = []
    vh = _vault_headers()
    if vh:
        try:
            r = requests.get(f"{VAULT_ADDR}/v1/{PKI_INT}/ca_chain", headers=vh, timeout=10)
            if r.status_code == 200:
                data = r.json().get('data', {})
                pems = data.get('certificate_chain') or []
                if pems:
                    chain_pems.extend([p.strip() for p in pems])
        except Exception:
            pass
        try:
            r = requests.get(f"{VAULT_ADDR}/v1/{PKI_ROOT}/cert/ca", headers=vh, timeout=10)
            if r.status_code == 200:
                pem = r.json().get('data', {}).get('certificate')
                if pem:
                    chain_pems.append(pem.strip())
        except Exception:
            pass
    if not chain_pems:
        # Fallback to local files mounted in API container or repo
        candidates = [
            '/opt/emqx/etc/certs/vault-ca-bundle.pem',
            os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../config/certificates/certs/emqx/vault-ca-bundle.pem')),
            os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../config/certificates/certs/emqx/vault-ca-bundle.pem')),
        ]
        for local_path in candidates:
            try:
                if os.path.exists(local_path):
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        norm = _normalize_pem_chain(content)
                        if norm:
                            return norm
            except Exception:
                continue
    # Normalize chain from Vault if present
    return _normalize_pem_chain('\n'.join(chain_pems))


@mqtt_quic_server_tls_bundle_bp.route('/api/v1/devices/<device_id>/mqtt-quic-server-tls-bundle.zip', methods=['GET'])
@require_auth
def download_mqtt_quic_server_tls_bundle(device_id: str):
    """Build a MQTT-QUIC Server-TLS bundle for a device.

    Bundle includes:
      - ca-chain.pem (intermediate + root) for server verification
      - mqtt-quic-config.json (connection configuration with username/password)
      - endpoints.json (MQTT-QUIC endpoint info)
      - README-MQTT-QUIC.txt (setup instructions and performance tips)

    Query params:
      - include_password=true  → perform secure password reset and include one-time password

    Note: MQTT-QUIC uses Server-TLS (not mTLS), so no client certificate is included.
          Devices authenticate via username (device_id) and password.
    """
    try:
        include_password = request.args.get('include_password', 'false').lower() == 'true'

        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({'message': 'Device not found'}), 404

        username = device.get('authentication', {}).get('mqtt_username') or device_id

        # Optionally reset MQTT password (one-time)
        mqtt_password = None
        reset_created_at = None
        reset_by_actor = None
        reset_expires_at = None
        if include_password:
            from ..services.device_service import reset_device_password, retrieve_reset_password
            # Use current user context for audit and retrieval
            initiator = (
                (g.current_user or {}).get('email')
                or (g.current_user or {}).get('username')
                or (g.current_user or {}).get('id')
                or 'bundle-api'
            )
            reset = reset_device_password(device_id, reset_by=initiator, reason='mqtt-quic-bundle-include')
            try:
                if reset and reset.get('reset_token'):
                    view = retrieve_reset_password(
                        device_id,
                        reset['reset_token'],
                        user_id=(g.current_user or {}).get('id') or (g.current_user or {}).get('_id'),
                        organization_id=(g.current_user or {}).get('organization_id')
                    )
                    if view and view.get('password'):
                        mqtt_password = view['password']
                        reset_created_at = view.get('created_at')
                        reset_by_actor = view.get('reset_by') or initiator
                        reset_expires_at = view.get('expires_at')
            except Exception:
                pass

        # Fetch CA chain for server verification
        ca_chain_pem = _fetch_ca_chain_pems()
        if not ca_chain_pem or 'BEGIN CERTIFICATE' not in ca_chain_pem:
            return jsonify({'message': 'Failed to obtain CA chain'}), 502

        # Build MQTT-QUIC configuration JSON
        mqtt_quic_config = {
            "protocol": "mqtts",
            "host": MQTT_QUIC_HOST,
            "port": MQTT_QUIC_PORT,
            "transport": "quic",
            "tls": {
                "enabled": True,
                "version": "1.3",
                "ca_file": "ca-chain.pem",
                "verify_server": True,
                "verify_mode": "server-only"
            },
            "auth": {
                "method": "username_password",
                "username": username,
                "password": mqtt_password or "<retrieve-via-password-reset>"
            },
            "endpoint": f"mqtts://{MQTT_QUIC_HOST}:{MQTT_QUIC_PORT}",
            "connection": {
                "keepalive": 60,
                "clean_session": True,
                "connect_timeout": 10
            }
        }

        # Build endpoints.json
        endpoints = {
            "mqtt_quic": f"mqtts://{MQTT_QUIC_HOST}:{MQTT_QUIC_PORT}",
            "transport": "quic",
            "protocol": "MQTT 3.1.1 / 5.0 over QUIC",
            "tls_version": "1.3",
            "auth_method": "username_password"
        }

        # Build README-MQTT-QUIC.txt
        readme = f"""TESA IoT Platform — MQTT over QUIC Server-TLS Bundle
========================================================

Files included:
- ca-chain.pem — CA certificate chain for server verification (intermediate + root)
- mqtt-quic-config.json — MQTT-QUIC connection configuration
- endpoints.json — MQTT-QUIC endpoint information
- README-MQTT-QUIC.txt — This file (setup instructions)

Connection Details:
-------------------
Endpoint: mqtts://{MQTT_QUIC_HOST}:{MQTT_QUIC_PORT}
Transport: QUIC (UDP-based)
TLS Version: 1.3 (mandatory, built into QUIC)
Authentication: Username/Password (Server-TLS mode)

Device Credentials:
-------------------
Username (Device ID): {username}
Password: {mqtt_password or '<Use password reset in Credentials tab>'}

Important Notes:
----------------
1. MQTT over QUIC uses UDP port {MQTT_QUIC_PORT}, not TCP
2. TLS 1.3 is mandatory and built into QUIC protocol (RFC 9001)
3. This is Server-TLS mode (NOT mTLS):
   - Server presents certificate (verified by ca-chain.pem)
   - Client authenticates with username/password
   - No client certificate required
4. For mTLS authentication, use MQTTS bundle (port 8883) instead

Performance Benefits:
---------------------
- 50% faster initial connection (1-RTT vs 2-RTT)
- 90% faster reconnection (0-RTT session resumption)
- Connection migration (survives IP address changes)
- Better performance on weak/intermittent networks
- No head-of-line blocking (independent stream multiplexing)

Use Cases:
----------
- Internet of Vehicles (IoV) — seamless connectivity while moving
- Mobile IoT devices — weak/intermittent cellular networks
- Low-latency applications — real-time control systems
- High-density deployments — resource-efficient connections

Network Requirements:
---------------------
- Firewall must allow UDP port {MQTT_QUIC_PORT} outbound
- Some corporate firewalls may block UDP traffic
- If QUIC unavailable, use MQTTS (TCP port 8884) as alternative

Security:
---------
- TLS 1.3 encryption (mandatory)
- Server identity verified via CA certificate chain
- Credentials transmitted securely
- Password should be stored securely on device (encrypted storage recommended)

Setup Instructions:
-------------------

1. Extract this bundle to your device
2. Embed ca-chain.pem in your device firmware
3. Use mqtt-quic-config.json for connection parameters
4. Implement MQTT client with QUIC support (e.g., NanoSDK, Paho MQTT-QUIC)

Example Client Libraries:
-------------------------
- C/C++: NanoSDK (https://github.com/nanomq/NanoSDK)
- Python: paho-mqtt with QUIC support
- Rust: rumqtt with QUIC backend
- Go: paho.mqtt.golang with QUIC transport

Code Examples:
--------------
See tutorial/examples/mqtt_quic-connectivity/ for:
- C/C++ example using NanoSDK
- Python example using paho-mqtt
- Connection error handling
- Reconnection logic

Troubleshooting:
----------------
- Connection timeout: Check firewall allows UDP {MQTT_QUIC_PORT}
- Certificate error: Verify ca-chain.pem is loaded correctly
- Authentication failed: Reset password in Credentials tab
- QUIC not available: Check if client library supports QUIC transport

Support:
--------
- Documentation: https://tesaiot.github.io/developer-hub
- Contact: your platform administrator
"""

        # Append Evidence block for transparency
        try:
            actor_email = (g.current_user or {}).get('email') or (g.current_user or {}).get('username')
            actor_id = (g.current_user or {}).get('id') or (g.current_user or {}).get('_id')
            actor_role = (g.current_user or {}).get('role')
            actor_org = (g.current_user or {}).get('organization_id')
        except Exception:
            actor_email = actor_id = actor_role = actor_org = None
        now_iso = datetime.utcnow().isoformat() + 'Z'
        readme_evidence = (
            "\nEvidence & Logging:\n"
            "-------------------\n"
            f"- Bundle generated at (UTC): {now_iso}\n"
            f"- Requested by: {actor_email or actor_id or '<unknown>'} (role: {actor_role or '-'}, org: {actor_org or '-'})\n"
            f"- Include Password: {'true' if include_password else 'false'}\n"
        )

        # If a password reset was performed for inclusion, append reset evidence
        if include_password and mqtt_password is not None:
            if reset_created_at:
                readme_evidence += f"- Password reset at (UTC): {reset_created_at}\n"
            if reset_by_actor:
                readme_evidence += f"- Password reset by: {reset_by_actor}\n"
            if actor_role or actor_org:
                readme_evidence += f"- Actor context: role={actor_role or '-'}, org={actor_org or '-'}\n"
            if reset_expires_at:
                readme_evidence += f"- One-time view expires at (UTC): {reset_expires_at}\n"
            readme_evidence += "\n⚠️  SECURITY: Password shown once. Store securely on device (encrypted storage).\n"

        # Build ZIP bundle
        mem = BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('ca-chain.pem', ca_chain_pem)
            zf.writestr('mqtt-quic-config.json', json.dumps(mqtt_quic_config, indent=2))
            zf.writestr('endpoints.json', json.dumps(endpoints, indent=2))
            zf.writestr('README-MQTT-QUIC.txt', readme + readme_evidence)

        mem.seek(0)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{device_id}-mqtt-quic-server-tls-bundle-{ts}.zip"
        return Response(
            mem.read(),
            status=200,
            headers={
                'Content-Type': 'application/zip',
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            from ..core.logging import logger as _logger
            _logger.error(f"MQTT-QUIC bundle error for {device_id}: {e}\n{tb}")
        except Exception:
            pass
        return jsonify({'error': 'MQTT_QUIC_BUNDLE_GENERATION_FAILED', 'message': str(e)}), 500
