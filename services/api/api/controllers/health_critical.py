# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from flask import Blueprint, jsonify, request, current_app

health_critical_bp = Blueprint('health_critical', __name__)

@health_critical_bp.route('/api/v1/health/critical', methods=['GET'])
def critical_health():
    """Check critical routes return 200/401 (not 404/5xx).

    Query params:
      - device_id: device id to probe
    """
    device_id = request.args.get('device_id') or 'e919a2f9-ad08-40be-a539-bef6b3b678a4'
    routes = {
        'server_tls_bundle': f"/api/v1/devices/{device_id}/server-tls-bundle.zip",
        'https_mtls_bundle': f"/api/v1/certificates/devices/{device_id}/certificate/download/https-mtls-bundle",
    }
    results = {}
    ok = True
    try:
        # Use app test client to avoid external network
        with current_app.test_client() as c:
            for name, path in routes.items():
                rv = c.head(path)
                code = rv.status_code
                results[name] = {'path': path, 'status': code}
                if code not in (200, 401):
                    ok = False
    except Exception as e:
        return jsonify({'status': 'fail', 'error': str(e)}), 500
    return jsonify({'status': 'ok' if ok else 'degraded', 'results': results}), (200 if ok else 500)

