# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Community Edition compatibility shims.
#
# The admin UI polls a few endpoints on every page load that belong to features
# NOT shipped in the single-organization Community Edition (notifications feed,
# license server, per-organization UI customization). Without these routes the
# SPA logs a stream of harmless-but-noisy 404s. These read-only stubs return
# benign CE defaults (no notifications, the community license, default UI) so the
# console stays clean and the UI gets sensible values. They expose no data and
# require no auth.
from flask import Blueprint, jsonify

ce_compat_bp = Blueprint('ce_compat', __name__)


@ce_compat_bp.route('/api/v1/notifications', methods=['GET'])
def list_notifications():
    """No notification subsystem in CE — return an empty feed."""
    return jsonify({
        'notifications': [],
        'unread_count': 0,
        'total': 0,
        'status': 'success',
    }), 200


@ce_compat_bp.route('/api/v1/license', methods=['GET'])
def get_license():
    """CE is the single-organization community edition (no license server)."""
    return jsonify({
        'id': 'license-community-001',
        'edition': 'community',
        'type': 'community',
        'isActive': True,
        'organizationId': 'default-org',
        'organizationName': 'Default Organization',
        'features': {},
        'limits': {'organizations': 1, 'devices': -1, 'users': -1},
    }), 200


@ce_compat_bp.route(
    '/api/v1/ui-customization/organizations/<org_id>/ui-configuration',
    methods=['GET'])
def get_ui_configuration(org_id):
    """No per-org UI customization in CE — return defaults."""
    return jsonify({
        'organization_id': org_id,
        'ui_elements': {},
        'tier': 'COMMUNITY',
    }), 200


@ce_compat_bp.route('/api/v1/dashboard/compliance/summary', methods=['GET'])
def compliance_summary():
    """Baseline compliance posture for the Community Edition.

    The UI's compliance indicator falls back to its built-in baseline if this is
    absent; serving it keeps the console clean and reflects the controls CE ships
    (ETSI EN 303 645 alignment, TLS/mTLS, Vault PKI, audit logging)."""
    items = [
        {'name': 'ETSI EN 303 645', 'standard': 'IoT baseline',
         'status': 'compliant', 'category': 'standards'},
        {'name': 'Data Encryption', 'standard': 'TLS 1.2/1.3 + mTLS',
         'status': 'compliant', 'category': 'transport'},
        {'name': 'Certificate Management', 'standard': 'Vault PKI',
         'status': 'compliant', 'category': 'identity'},
        {'name': 'Access Control', 'standard': 'RBAC + JWT',
         'status': 'compliant', 'category': 'access'},
        {'name': 'Audit Logging', 'standard': 'audit trail',
         'status': 'compliant', 'category': 'governance'},
    ]
    return jsonify({'data': {'compliance_items': items}}), 200
