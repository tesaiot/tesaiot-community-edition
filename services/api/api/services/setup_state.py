# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# First-run setup state.
#
# The single source of truth for "has this instance been claimed?" is the
# keyed singleton ``db.system_config {_id: 'setup'}`` — the same idiom CE uses
# for the 'ca_chain' and 'pki_roles' documents, so the flag lives in the same
# database as the admin accounts and cannot desynchronize from them across
# container redeploys the way a config-file lock could.
#
# The effective check is deliberately a disjunction (flag set OR a human admin
# exists): a pre-wizard install that seeded its admin from .env is treated as
# set up the moment it boots this code, and the flag is backfilled.
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SETUP_DOC_ID = 'setup'

# Human administrator roles. The 'service' role (e.g. the MQTT bridge account)
# never counts towards "the instance has an owner".
ADMIN_ROLES = ['admin', 'super_admin', 'organization_admin', 'org_admin', 'platform_admin']


def admin_exists(db) -> bool:
    """True if at least one human administrator account exists."""
    try:
        return db.users.count_documents(
            {'role': {'$in': ADMIN_ROLES}, 'is_service_account': {'$ne': True}},
            limit=1,
        ) > 0
    except Exception as exc:
        # Fail CLOSED for the wizard: if we cannot prove the instance is
        # unclaimed, treat it as claimed so setup endpoints refuse.
        logger.error(f"admin_exists check failed (treating as claimed): {exc}")
        return True


def setup_flag(db) -> dict:
    """Return the raw setup document ({} when absent)."""
    try:
        return db.system_config.find_one({'_id': SETUP_DOC_ID}) or {}
    except Exception as exc:
        logger.error(f"setup flag read failed: {exc}")
        return {}


def is_setup_completed(db) -> bool:
    """The gate every /setup mutation checks: flag set OR an admin exists."""
    if setup_flag(db).get('setup_completed'):
        return True
    return admin_exists(db)


def mark_setup_completed(db, mode: str, completed_by: str = '') -> None:
    """Persist the one-shot completion flag.

    mode: 'wizard' (claimed via the web wizard), 'env' (seeded from
    ADMIN_* environment variables), or 'legacy' (backfilled on upgrade for an
    instance whose admin predates the flag).
    """
    try:
        from ..core.config import Config
        version = ''
        try:
            version = Config.get_version()  # may not exist; best effort
        except Exception:
            pass
        db.system_config.update_one(
            {'_id': SETUP_DOC_ID},
            {'$set': {
                'setup_completed': True,
                'mode': mode,
                'completed_by': completed_by,
                'completed_at': datetime.utcnow().isoformat() + 'Z',
                'version': version,
            }},
            upsert=True,
        )
        logger.info(f"Setup marked completed (mode={mode}, by={completed_by or 'n/a'})")
    except Exception as exc:
        logger.error(f"Failed to persist setup flag: {exc}")
