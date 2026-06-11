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

server_tls_bundle_bp = Blueprint('server_tls_bundle', __name__)

VAULT_ADDR = os.getenv('VAULT_ADDR', 'http://tesa-vault:8200')
PKI_INT = os.getenv('PKI_INT_MOUNT', 'pki-int')
PKI_ROOT = os.getenv('PKI_ROOT_MOUNT', 'pki-root')
VAULT_TOKEN = os.getenv('VAULT_TOKEN') or os.getenv('VAULT_ROOT_TOKEN')

# Public endpoints (env-driven). Server‑TLS MQTT should use TLS (username/password) port, not mTLS
BROKER_HOST = os.getenv('TESA_PUBLIC_MQTT_HOST', 'localhost')
BROKER_PORT = int(os.getenv('TESA_MQTT_BROKER_PORT', os.getenv('TESA_PUBLIC_MQTT_TLS_PORT', '8884')))
API_BASE = os.getenv('TESA_API_BASE_HTTPS', os.getenv('TESA_PUBLIC_API_BASE_URL', 'https://localhost'))
INGEST_BASE = os.getenv('TESA_PUBLIC_INGEST_BASE_URL', f"{API_BASE}:9444")


def _vault_headers():
    # Optional: Only used when VAULT_TOKEN provided. Otherwise, caller should skip Vault calls.
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
    """Return concatenated PEM (intermediate + root)."""
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


@server_tls_bundle_bp.route('/api/v1/devices/<device_id>/server-tls-bundle.zip', methods=['GET'])
@require_auth
def download_server_tls_bundle(device_id: str):
    """Build a Server‑TLS complete bundle for a device.

    Bundle includes:
      - ca-chain.pem (intermediate + root)
      - mqtt-credentials.txt (username/password placeholder)
      - https-api-credentials.txt (API endpoint + API key placeholder)
      - README.txt (instructions)

    Query params:
      - include_password=true  → perform secure password reset and include one-time password
      - include_api_key=true   → regenerate API key and include new key
    """
    try:
        include_password = request.args.get('include_password', 'false').lower() == 'true'
        include_api_key = request.args.get('include_api_key', 'false').lower() == 'true'
        flavor = (request.args.get('flavor') or '').lower()  # '', 'mqtt', 'https'

        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({'message': 'Device not found'}), 404

        username = device.get('authentication', {}).get('mqtt_username') or device_id
        api_key = device.get('api_key')

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
            reset = reset_device_password(device_id, reset_by=initiator, reason='server-tls-bundle-include')
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

        # Optionally regenerate API key
        if include_api_key:
            # simple regeneration stored on device record
            # Reuse endpoint logic by calling function is complex; instead regenerate here
            import secrets
            prefix = device_id.replace('-', '')[:8].lower()
            api_key = f"tesa_dak_{prefix}_{secrets.token_hex(16)}"
            db.devices.update_one({'device_id': device_id}, {'$set': {'api_key': api_key, 'authentication.api_key': api_key}})

        # Files
        ca_chain_pem = _fetch_ca_chain_pems()
        if not ca_chain_pem or 'BEGIN CERTIFICATE' not in ca_chain_pem:
            return jsonify({'message': 'Failed to obtain CA chain'}), 502

        mqtt_txt = (
            f"MQTT Credentials for Device: {device.get('name','') or device_id}\n"
            f"================================\n\n"
            f"Device ID (Username): {username}\n"
            f"Password: {mqtt_password or '<retrieve-via-reset>'}\n\n"
            f"MQTT Broker: mqtts://{BROKER_HOST}:{BROKER_PORT}\n"
            f"Authentication Mode: Server-TLS (Password-based)\n"
        )

        # Build HTTPS credentials text (ensure defined within the request scope)
        https_txt = f"""HTTPs API Credentials for Device: {device.get('name','') or device_id}
================================

Device ID: {device_id}
API Key: {api_key or '<regenerate-via-UI/endpoint>'}

API Endpoint: {API_BASE}/api/v1/telemetry
Authentication: X-API-KEY header (device API key)

Example curl command:
curl -X POST {API_BASE}/api/v1/telemetry \
  -H "X-API-KEY: {api_key or '<api_key>'}" \
  -H "Content-Type: application/json" \
  -d '{{"device_id":"{device_id}","timestamp":"<ISO8601>","data":{{"temperature":25.5,"humidity":60}}}}'
"""

        readme = (
            "TESA IoT Platform — Server‑TLS Complete Bundle\n\n"
            "Files included:\n"
            "- ca-chain.pem — CA chain for TLS validation (intermediate + root)\n"
            "- mqtt-credentials.txt — MQTT username/password and broker address\n"
            "- https-api-credentials.txt — HTTPS endpoint and API key\n"
            "- endpoints.json — Service endpoint configuration\n"
            "- mqtt_client_config.h — PSoC/embedded MQTT client configuration header\n"
            "- telemetry/ — Auto-generated C code for telemetry serialization\n"
            "  - data_telemetry.h — Struct definitions and function prototypes\n"
            "  - data_telemetry.c — JSON serialization implementation\n"
            "  - README.md — Usage documentation\n\n"
            "Notes:\n"
            "- Passwords/API keys may be shown only once. Use reset/regenerate in Credentials tab if needed.\n"
            "- Broker: mqtts://{host}:{port} (Server‑TLS)\n"
            "- mqtt_client_config.h is pre-configured for Server-TLS mode (password-based authentication)\n"
            "- telemetry/ contains portable C code generated from your device's Data Schema\n".format(host=BROKER_HOST, port=BROKER_PORT)
        )

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
            f"- Bundle generated at (UTC): {now_iso}\n"
            f"- Requested by: {actor_email or actor_id or '<unknown>'} (role: {actor_role or '-'}, org: {actor_org or '-'})\n"
            f"- Include Password: {'true' if include_password else 'false'}\n"
            f"- Include API Key: {'true' if include_api_key else 'false'}\n"
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

        # Build zip
        mem = BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('ca-chain.pem', ca_chain_pem)
            if flavor in ('', 'mqtt'):
                zf.writestr('mqtt-credentials.txt', mqtt_txt)
            if flavor in ('', 'https'):
                zf.writestr('https-api-credentials.txt', https_txt)
            # Include endpoints.json for client configuration (flat keys)
            endpoints = {
                'ingest_base_url': INGEST_BASE,
                'api_base_url': API_BASE,
                'tls': {'require_mtls': False, 'alpn': ['h2', 'http/1.1']}
            }
            zf.writestr('endpoints.json', json.dumps(endpoints, indent=2))

            # Include mqtt_client_config.h for embedded clients (PSoC Edge)
            # Uses server_tls template which configures for password-based auth
            if flavor in ('', 'mqtt'):
                try:
                    from ..services.certificate_service import _build_mqtt_client_config_header_full
                    header_text = _build_mqtt_client_config_header_full(
                        device_id=device_id,
                        username=username,
                        auth_mode='server_tls',  # Selects mqtt_client_config_server_tls.h.template
                        ca_pem=ca_chain_pem,
                        cert_pem=None,  # Server TLS does not require client certificate
                        key_pem=None,   # Server TLS does not require private key
                        algorithm_label='N/A (Server TLS)'
                    )
                    zf.writestr('mqtt_client_config.h', header_text)
                except Exception as header_err:
                    # Log warning but don't fail bundle generation
                    try:
                        from ..core.logging import logger as _logger
                        _logger.warning(f"Failed to generate mqtt_client_config.h for {device_id}: {header_err}")
                    except Exception:
                        pass

            # Include auto-generated telemetry code (data_telemetry.c/.h)
            try:
                from ..services.telemetry_code_generator import add_telemetry_files_to_zip
                add_telemetry_files_to_zip(zf, device, folder_prefix='telemetry')
            except Exception as telemetry_err:
                # Log warning but don't fail bundle generation
                try:
                    from ..core.logging import logger as _logger
                    _logger.warning(f"Failed to generate telemetry code for {device_id}: {telemetry_err}")
                except Exception:
                    pass

            zf.writestr('README.txt', readme + readme_evidence)

        mem.seek(0)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        suffix = 'complete'
        if flavor in ('mqtt', 'https'):
            suffix = flavor
        filename = f"{device_id}-servertls-{suffix}-bundle-{ts}.zip"
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
            _logger.error(f"Server‑TLS bundle error for {device_id}: {e}\n{tb}")
        except Exception:
            pass
        return jsonify({'error': 'BUNDLE_GENERATION_FAILED', 'message': str(e)}), 500
