# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Organization-level API Key service (Community Edition).

The full platform manages organization API keys as dynamic APISIX consumers
(requires APISIX + etcd). The Community Edition runs APISIX in standalone YAML
mode (no etcd), so per-consumer gateway keys are not available. Instead, CE
stores organization API keys in MongoDB and validates them at the API tier
(the same pattern used for device API keys in ``api_key_service``). Keys are
stored only as a SHA-256 hash plus a short non-secret prefix; the plaintext key
is returned exactly once, at creation/rotation time.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from ..core.database import get_db

logger = logging.getLogger(__name__)

COLLECTION = 'org_api_keys'
DEFAULT_SCOPES = ['devices:read', 'telemetry:read', 'organizations:read']


def _hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _generate_key(org_id: str):
    """Return (plaintext_key, key_prefix). Format: tesaiot_org_<org8>_<hex32>."""
    org_prefix = (org_id or 'org').replace('-', '')[:8]
    plaintext = f"tesaiot_org_{org_prefix}_{secrets.token_hex(16)}"
    return plaintext, plaintext[:18]


def _public(doc: dict) -> dict:
    """Serialise a stored key document into the (secret-free) shape the UI expects."""
    def _iso(v):
        return v.isoformat() if isinstance(v, datetime) else v
    return {
        'id': doc.get('id'),
        'name': doc.get('name'),
        'description': doc.get('description', ''),
        'key_prefix': doc.get('key_prefix'),
        'scopes': doc.get('scopes', []),
        'status': doc.get('status', 'active'),
        'created_at': _iso(doc.get('created_at')),
        'expires_at': _iso(doc.get('expires_at')),
        'last_used': _iso(doc.get('last_used')),
        'usage_count': doc.get('usage_count', 0),
        'usage_limits': {'rate_limit': doc.get('rate_limit', 0)},
    }


def list_api_keys(organization_id: str):
    db = get_db()
    docs = db[COLLECTION].find({'organization_id': organization_id, 'status': {'$ne': 'deleted'}})
    return [_public(d) for d in docs]


def create_api_key(organization_id, name, description='', scopes=None,
                   rate_limit=100, expires_in_days=90, created_by=None):
    db = get_db()
    if not name:
        raise ValueError('name is required')
    scopes = scopes or list(DEFAULT_SCOPES)
    plaintext, key_prefix = _generate_key(organization_id)
    now = datetime.now()
    doc = {
        'id': str(uuid4()),
        'organization_id': organization_id,
        'name': name,
        'description': description or '',
        'key_hash': _hash(plaintext),
        'key_prefix': key_prefix,
        'scopes': scopes,
        'rate_limit': int(rate_limit or 0),
        'status': 'active',
        'created_at': now,
        'expires_at': now + timedelta(days=int(expires_in_days or 90)),
        'last_used': None,
        'usage_count': 0,
        'created_by': created_by,
    }
    db[COLLECTION].insert_one(dict(doc))
    result = _public(doc)
    # Plaintext key is returned exactly once and never stored.
    result['api_key'] = plaintext
    return result


def revoke_api_key(organization_id, key_id):
    db = get_db()
    res = db[COLLECTION].update_one(
        {'id': key_id, 'organization_id': organization_id},
        {'$set': {'status': 'revoked', 'revoked_at': datetime.now()}})
    return res.matched_count > 0


def rotate_api_key(organization_id, key_id):
    db = get_db()
    doc = db[COLLECTION].find_one({'id': key_id, 'organization_id': organization_id})
    if not doc:
        return None
    plaintext, key_prefix = _generate_key(organization_id)
    db[COLLECTION].update_one(
        {'id': key_id, 'organization_id': organization_id},
        {'$set': {'key_hash': _hash(plaintext), 'key_prefix': key_prefix,
                  'status': 'active', 'rotated_at': datetime.now()}})
    doc.update({'key_prefix': key_prefix, 'status': 'active'})
    result = _public(doc)
    result['api_key'] = plaintext
    return result


def get_api_key_metrics(organization_id, key_id):
    db = get_db()
    doc = db[COLLECTION].find_one({'id': key_id, 'organization_id': organization_id})
    if not doc:
        return None
    return {
        'id': key_id,
        'usage_count': doc.get('usage_count', 0),
        'last_used': doc.get('last_used').isoformat() if isinstance(doc.get('last_used'), datetime) else None,
        'rate_limit': doc.get('rate_limit', 0),
        'status': doc.get('status', 'active'),
        # CE validates at the API tier (no per-consumer gateway metrics in
        # APISIX standalone mode); detailed time-series usage is not collected.
        'series': [],
    }


def validate_api_key(api_key: str):
    """Validate a presented org API key. Returns the public doc or None."""
    if not api_key:
        return None
    db = get_db()
    doc = db[COLLECTION].find_one({'key_hash': _hash(api_key), 'status': 'active'})
    if not doc:
        return None
    if isinstance(doc.get('expires_at'), datetime) and doc['expires_at'] < datetime.now():
        return None
    db[COLLECTION].update_one({'id': doc['id']},
                              {'$set': {'last_used': datetime.now()},
                               '$inc': {'usage_count': 1}})
    # Include organization_id (omitted from the UI-facing _public shape) so the
    # auth layer can bind the request to the key's organization.
    result = _public(doc)
    result['organization_id'] = doc.get('organization_id')
    return result
