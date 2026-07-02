# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# First-run setup wizard API (Community Edition).
#
# Unauthenticated but strictly gated:
#   GET  /api/v1/setup/status        read-only; safe fields only
#   POST /api/v1/setup/verify-token  constant-time token pre-check (fail-closed)
#   POST /api/v1/setup/complete      atomic claim: token AND not-completed AND
#                                    no human admin exists
#
# Gating model (see PRINCIPLES of the design: Jenkins-style one-time token):
# the SETUP_TOKEN is generated per install into .env and printed by the
# installer, so presenting it proves possession of the host filesystem — the
# same proof Nextcloud's CAN_INSTALL demands. Once setup completes (or any
# human admin exists) every mutating route refuses with 410 REGARDLESS of the
# token: the wizard is disabled server-side, never merely hidden, and later
# probes are logged as security events.
import hmac
import logging
import os
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from ..core.database import get_db
from ..services.setup_state import is_setup_completed, mark_setup_completed
from ..utils.validation import validate_email, validate_password, sanitize_string

logger = logging.getLogger(__name__)

setup_bp = Blueprint('setup', __name__, url_prefix='/api/v1/setup')


# ---------------------------------------------------------------------------
# Token gate (fail closed, constant time) — same idiom as the EMQX webhook
# shared-secret check in emqx_auth.py.
# ---------------------------------------------------------------------------
def _configured_token():
    token = (os.getenv('SETUP_TOKEN') or '').strip()
    if not token or token.startswith('CHANGEME'):
        return None  # unset/placeholder -> the wizard can never be claimed
    return token


def _token_matches(presented) -> bool:
    real = _configured_token()
    if not real or not presented:
        return False
    return hmac.compare_digest(str(presented), real)


def _bearer_token():
    header = request.headers.get('Authorization', '')
    parts = header.split(' ')
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    return None


def _version() -> str:
    for path in ('/app/VERSION.txt',
                 os.path.join(os.path.dirname(__file__), '../../../VERSION.txt')):
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            continue
    return 'unknown'


def _refuse_completed(action: str):
    """410 for mutating setup routes once the instance is claimed.

    Logged as a security event: a live-but-refusing endpoint lets us tell
    post-setup probes apart from routing noise (a deleted route could not).
    """
    logger.warning(
        f"[SECURITY] Setup endpoint '{action}' probed after setup completion "
        f"from {request.remote_addr}"
    )
    return jsonify({
        'error': 'Setup has already been completed on this instance.',
        'code': 'SETUP_ALREADY_COMPLETED',
    }), 410


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@setup_bp.route('/status', methods=['GET'])
def setup_status():
    """Safe, unauthenticated bootstrap probe for the SPA.

    Exposes nothing sensitive: once setup is complete it only says so."""
    db = get_db()
    completed = True if db is None else is_setup_completed(db)

    payload = {
        'setup_required': not completed,
        'version': _version(),
    }
    if not completed:
        # Pre-fill hints for the wizard (public-by-design values only).
        payload['domain'] = os.getenv('DOMAIN', 'localhost')
        payload['admin_email_prefill'] = os.getenv('ADMIN_EMAIL', 'admin@localhost')
        payload['timezone'] = os.getenv('TZ', 'UTC')
        payload['token_configured'] = _configured_token() is not None

        # Lightweight service health so step 1 can show readiness.
        health = {'mongodb': db is not None}
        try:
            from ..core.database import get_redis
            health['redis'] = get_redis() is not None
        except Exception:
            health['redis'] = False
        try:
            from ..core.database import get_vault
            health['vault'] = get_vault() is not None
        except Exception:
            health['vault'] = False
        payload['health'] = health
    return jsonify(payload), 200


@setup_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Fast-fail token pre-check so the wizard can gate step 1 -> 2."""
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database unavailable', 'code': 'DB_UNAVAILABLE'}), 503
    if is_setup_completed(db):
        return _refuse_completed('verify-token')

    data = request.get_json(silent=True) or {}
    if _token_matches(data.get('token')):
        return jsonify({'valid': True}), 200

    logger.warning(f"[SECURITY] Invalid setup token presented from {request.remote_addr}")
    return jsonify({'valid': False, 'error': 'Invalid setup token', 'code': 'INVALID_SETUP_TOKEN'}), 401


@setup_bp.route('/complete', methods=['POST'])
def complete_setup():
    """Atomically claim the instance: create the administrator, name the
    organization, and permanently close the wizard."""
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database unavailable', 'code': 'DB_UNAVAILABLE'}), 503
    if is_setup_completed(db):
        return _refuse_completed('complete')

    if not _token_matches(_bearer_token()):
        logger.warning(f"[SECURITY] Setup completion attempted with invalid token from {request.remote_addr}")
        return jsonify({'error': 'Invalid setup token', 'code': 'INVALID_SETUP_TOKEN'}), 401

    data = request.get_json(silent=True) or {}
    email = sanitize_string((data.get('email') or '').strip().lower(), 254)
    username = sanitize_string((data.get('username') or 'admin').strip(), 100)
    password = data.get('password') or ''
    org_name = sanitize_string((data.get('organization_name') or '').strip(), 200)
    timezone = sanitize_string((data.get('timezone') or '').strip(), 64)

    if not validate_email(email):
        return jsonify({'error': 'Invalid email address', 'field': 'email', 'code': 'INVALID_EMAIL'}), 400
    is_valid, pw_error = validate_password(password)
    if not is_valid:
        return jsonify({'error': pw_error, 'field': 'password', 'code': 'WEAK_PASSWORD'}), 400
    if db.users.find_one({'email': email}):
        return jsonify({'error': 'A user with this email already exists', 'field': 'email',
                        'code': 'EMAIL_EXISTS'}), 409

    from ..core.config import Config
    from ..services.user_service import create_user_in_vault

    # Same creation path as the env seeder (Vault credential with bcrypt
    # fallback) so wizard- and env-created admins are indistinguishable.
    vault_success, password_hash = create_user_in_vault(username, password)

    effective_org_name = org_name or 'Default Organization'
    now = datetime.utcnow()
    user_doc = {
        '_id': str(ObjectId()),
        'email': email,
        'name': 'Organization Admin',
        'role': 'admin',
        'organization': effective_org_name,
        'organization_id': Config.DEFAULT_ORG_ID,
        'vault_user': username,
        'status': 'active',
        'created_at': now,
    }
    if password_hash:
        user_doc['password_hash'] = password_hash
    db.users.insert_one(user_doc)

    # Name the single organization (DB is authoritative for reads).
    org_set = {
        'name': effective_org_name,
        'display_name': effective_org_name,
        'contact_email': email,
        'updated_at': now.isoformat() + 'Z',
    }
    if timezone:
        org_set['timezone'] = timezone
    db.organizations.update_one(
        {'_id': Config.DEFAULT_ORG_ID},
        {'$set': org_set,
         '$setOnInsert': {
             'organization_id': Config.DEFAULT_ORG_ID,
             'plan': 'community',
             'status': 'active',
             'type': 'default',
             'created_at': now.isoformat() + 'Z',
             'created_by': 'setup_wizard',
         }},
        upsert=True,
    )

    mark_setup_completed(db, mode='wizard', completed_by=email)

    # Best-effort audit trail of the claim (who/where/when).
    try:
        from ..services.audit_service import audit_log, AuditAction
        audit_log(
            action=AuditAction.USER_CREATE,
            user={'email': email, 'role': 'admin', 'type': 'setup_wizard'},
            resource_type='system',
            resource_id='setup',
            details={'event': 'first_run_setup_completed',
                     'organization_name': effective_org_name,
                     'auth_backend': 'vault' if vault_success else 'bcrypt'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
        )
    except Exception as audit_err:
        logger.debug(f"Setup audit log skipped: {audit_err}")

    logger.info(f"✅ First-run setup completed: admin {email} created via wizard "
                f"({'Vault' if vault_success else 'bcrypt'} auth)")
    return jsonify({
        'success': True,
        'email': email,
        'organization_name': effective_org_name,
        'message': 'Setup complete. The setup token is now permanently inert.',
    }), 201
