# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESAIoT Community Edition - Organization Controller (single-organization, read-only).

The self-host Community Edition targets a SINGLE organization. Multi-tenant
organization management is out of scope, so this module exposes only read-only
endpoints that describe the one default organization:

    GET  /api/v1/organizations          -> list containing the single org
    GET  /api/v1/organizations/<org_id> -> details of the single org
    GET  /api/v1/organizations/settings -> read-only org settings

The following capabilities from the full platform have been intentionally
removed as out of scope: creating/deleting/updating organizations, the
multi-tenant sub-organization hierarchy (tree/move/hierarchy), per-org usage
reporting, billing, plan upgrades, and the billing-tracked APISIX consumer
API-key lifecycle.
"""

import logging

from flask import Blueprint, jsonify, g

from ..core.config import Config
from ..core.exceptions import NotFoundError
from ..core.auth import require_auth
from ..services import organization_service

logger = logging.getLogger(__name__)

# Create Blueprint
organizations_bp = Blueprint('organizations', __name__)


def _resolve_single_org(current_user):
    """Resolve the one organization visible to the current user.

    Prefers the user's bound organization, then any record returned by the
    service, and finally falls back to the configured default org id/name so the
    endpoint always returns a coherent single-org payload.
    """
    org = None

    org_id = current_user.get('organization_id') if current_user else None
    if org_id:
        try:
            org = organization_service.get_organization_by_id(org_id)
        except Exception:  # noqa: BLE001 - degrade to fallback below
            org = None

    if not org:
        try:
            orgs = organization_service.get_all_organizations(current_user) or []
            if orgs:
                org = orgs[0]
        except Exception:  # noqa: BLE001 - degrade to fallback below
            org = None

    if not org:
        # Synthesize the configured default organization so the single-org
        # contract holds even before any record exists in the database.
        org = {
            '_id': Config.DEFAULT_ORG_ID,
            'organization_id': Config.DEFAULT_ORG_ID,
            'name': Config.DEFAULT_ORG_NAME,
            'display_name': Config.DEFAULT_ORG_NAME,
        }

    return org


@organizations_bp.route('', methods=['GET'])
@organizations_bp.route('/', methods=['GET'])
@require_auth
def get_organizations():
    """Return the single default organization wrapped in a list.

    Kept for frontend compatibility (organization selectors); always one item.

    Returns:
        200: List with the single organization
        500: Server error
    """
    try:
        org = _resolve_single_org(g.current_user)
        try:
            formatted = organization_service.format_organization_with_usage(org)
        except Exception:  # noqa: BLE001 - fall back to the raw document
            formatted = org

        return jsonify({
            'success': True,
            'organizations': [formatted],
            'total': 1,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching organization: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@organizations_bp.route('/settings', methods=['GET'])
@require_auth
def get_organization_settings():
    """Return read-only settings for the single organization."""
    try:
        org = _resolve_single_org(g.current_user)
        settings = org.get('settings', {}) if isinstance(org, dict) else {}

        resolved_settings = {
            'auto_device_registration': settings.get('auto_device_registration', True),
            'device_approval_required': settings.get('device_approval_required', False),
            'email_notifications': settings.get('email_notifications', True),
            'webhook_notifications': settings.get('webhook_notifications', False),
            'data_retention_days': settings.get('data_retention_days', 90),
            'max_devices': settings.get('max_devices', 1000),
            'timezone': settings.get('timezone', 'UTC'),
        }

        org_id = org.get('organization_id') or org.get('_id') if isinstance(org, dict) else Config.DEFAULT_ORG_ID

        return jsonify({
            'organization_id': str(org_id),
            'settings': resolved_settings,
        }), 200

    except Exception as e:
        logger.error(f"Error getting organization settings: {e}")
        return jsonify({'error': 'Failed to get organization settings'}), 500


@organizations_bp.route('/<org_id>', methods=['GET'])
@require_auth
def get_organization(org_id):
    """Return details of the single organization.

    Returns:
        200: Organization details
        404: Organization not found
        500: Server error
    """
    try:
        organization = None
        try:
            organization = organization_service.get_organization_by_id(org_id)
        except NotFoundError:
            organization = None
        except Exception:  # noqa: BLE001 - degrade to single-org resolver
            organization = None

        if not organization:
            organization = _resolve_single_org(g.current_user)

        if not organization:
            return jsonify({'error': 'Organization not found'}), 404

        try:
            formatted = organization_service.format_organization_with_usage(organization)
        except Exception:  # noqa: BLE001 - fall back to the raw document
            formatted = organization

        return jsonify({
            'success': True,
            'organization': formatted,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching organization: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
