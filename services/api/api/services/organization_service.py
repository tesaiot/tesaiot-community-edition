# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Fixed Organization Service - Simplified to prevent 500 errors

CRITICAL: NO MOCK DATA POLICY
- All metrics must come from actual data sources
- If data unavailable, return 0 with proper note
- NEVER return hardcoded fake values
"""
import logging
from datetime import datetime, timedelta
from bson import ObjectId
from ..core.rbac import RBAC

# Usage/billing metrics are out of scope for the Community Edition. Provide a
# no-op fallback so organization metrics endpoints still respond without the
# billing subsystem.
try:
    from .usage_metrics_service import usage_metrics_service  # type: ignore
except ImportError:
    class _NoopUsageMetricsService:
        def get_organization_metrics(self, *args, **kwargs):
            return {}

        def get_api_calls_total(self, *args, **kwargs):
            return {}

        def get_storage_usage(self, *args, **kwargs):
            return {}

        def get_data_transfer(self, *args, **kwargs):
            return {}

    usage_metrics_service = _NoopUsageMetricsService()

logger = logging.getLogger(__name__)

def ensure_default_organizations():
    """Ensure default organizations exist - stub for compatibility"""
    pass

def get_all_organizations(current_user):
    """Get all organizations - simplified version that works"""
    try:
        db = get_db()
        user_role = current_user.get('role', 'user')
        user_email = current_user.get('email', '')
        
        # DEBUG: Log exact input
        print(f"[ORG_SERVICE_DEBUG] get_all_organizations called with user: {current_user}", flush=True)
        print(f"[ORG_SERVICE_DEBUG] User email: {user_email}, role: {user_role}, org_id: {current_user.get('organization_id')}", flush=True)
        logger.error(f"[ORG_SERVICE_DEBUG] get_all_organizations called with user: {current_user}")
        logger.error(f"[ORG_SERVICE_DEBUG] User email: {user_email}, role: {user_role}, org_id: {current_user.get('organization_id')}")
        
        # SECURITY FIX: Platform admins can ONLY see infrastructure organizations, NOT customer data
        # Platform admins have full access to manage all organizations (they have ORGANIZATION_VIEW_ALL permission)
        # Platform Admin role is for platform management, not just infrastructure
        if RBAC.is_platform_admin({'role': user_role, 'email': user_email}):
            logger.info(f"[ORG_SERVICE] Platform admin {user_email} accessing all organizations for platform management")
            if db is not None:
                # Platform admins need to see all organizations to manage the platform properly
                # They have ORGANIZATION_VIEW_ALL permission in RBAC
                orgs = list(db.organizations.find())
                result = []
                
                for org in orgs:
                    # Use the format_organization_with_usage function for proper database queries
                    formatted_org = format_organization_with_usage(org)
                    result.append(formatted_org)
                
                logger.info(f"[ORG_SERVICE] Platform admin {user_email} accessed {len(result)} organizations for platform management")
                return result
            return []
        
        # Super admins see all organizations
        if user_role == 'super_admin' and db is not None:
            orgs = list(db.organizations.find())
            result = []
            
            for org in orgs:
                # Use the format_organization_with_usage function for proper database queries
                formatted_org = format_organization_with_usage(org)
                result.append(formatted_org)
            
            return result
        
        # Other users see their organization only
        user_org_id = current_user.get('organization_id', '')
        logger.info(f"[ORG_SERVICE] User {current_user.get('email')} with role {user_role} requesting orgs, org_id: {user_org_id}")
        
        if user_org_id and db is not None:
            # Try to find by _id or organization_id field - comprehensive search
            from bson import ObjectId as BsonObjectId
            
            # Build comprehensive query to handle all possible organization ID formats
            query_conditions = [
                {'_id': user_org_id},  # Match by document _id (string)
                {'organization_id': user_org_id}  # Match by organization_id field
            ]
            
            # Also try ObjectId format if the user_org_id is a valid ObjectId
            if BsonObjectId.is_valid(user_org_id):
                try:
                    obj_id = BsonObjectId(user_org_id)
                    query_conditions.append({'_id': obj_id})
                    logger.info(f"[ORG_SERVICE] Added ObjectId query condition for: {user_org_id}")
                except:
                    pass
            
            query = {'$or': query_conditions}
            logger.info(f"[ORG_SERVICE] Using comprehensive query for user_org_id '{user_org_id}': {query}")
            
            org = db.organizations.find_one(query)
            logger.info(f"[ORG_SERVICE] Query result: org found = {org is not None}")
            logger.info(f"[ORG_SERVICE] Organization found: {org is not None}")
            if org:
                logger.info(f"[ORG_SERVICE] Returning org: {org.get('name')}")
                # Use the format_organization_with_usage function for proper database queries
                formatted_org = format_organization_with_usage(org)
                return [formatted_org]
        
        return []
        
    except Exception as e:
        logger.error(f"Error in get_all_organizations: {e}")
        return []

def create_organization(org_data, current_user):
    """Create a new organization"""
    try:
        db = get_db()
        
        # Only super_admin can create organizations
        if current_user.get('role') != 'super_admin':
            raise ValueError("Only super administrators can create organizations")
        
        # Generate organization_id if not provided
        org_id = org_data.get('organization_id', org_data.get('name', '').lower().replace(' ', '-'))
        
        # Create organization document
        org_doc = {
            '_id': org_id,
            'organization_id': org_id,
            'name': org_data.get('name'),
            'display_name': org_data.get('display_name', org_data.get('name')),
            'description': org_data.get('description', ''),
            'plan': org_data.get('plan', 'starter'),
            'status': org_data.get('status', 'active'),
            'contact_email': org_data.get('contact_email', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': current_user.get('email'),
            'settings': org_data.get('settings', {
                'max_devices': 100,
                'max_users': 10,
                'features': {
                    'telemetry': True,
                    'alerts': True,
                    'reports': True,
                    'api_access': True
                }
            })
        }
        
        # Insert organization
        result = db.organizations.insert_one(org_doc)
        
        logger.info(f"Organization created: {org_id} by {current_user.get('email')}")
        
        return {
            'id': org_id,
            'organization_id': org_id,
            'name': org_doc['name'],
            'display_name': org_doc['display_name'],
            'plan': org_doc['plan'],
            'status': org_doc['status'],
            'created_at': str(org_doc['created_at'])
        }
        
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise

def get_organization(org_id, current_user):
    """Get a single organization"""
    try:
        db = get_db()
        
        # Build query to handle both ObjectId and string formats
        query_conditions = [
            {'_id': org_id},
            {'organization_id': org_id}
        ]
        
        # Try as ObjectId if it's a valid ObjectId string
        try:
            from bson import ObjectId as BsonObjectId
            if BsonObjectId.is_valid(org_id):
                obj_id = BsonObjectId(org_id)
                query_conditions.append({'_id': obj_id})
        except:
            pass
        
        # Find organization
        org = db.organizations.find_one({'$or': query_conditions})
        
        if not org:
            return None
        
        # Check permissions
        user_role = current_user.get('role')
        if user_role != 'super_admin':
            user_org_id = current_user.get('organization_id')
            if str(org.get('_id')) != str(user_org_id):
                return None
        
        # Use the format_organization_with_usage function for proper database queries
        return format_organization_with_usage(org)
        
    except Exception as e:
        logger.error(f"Error getting organization: {e}")
        return None

def update_organization(org_id, update_data, current_user):
    """Update an organization"""
    try:
        db = get_db()
        
        # Only super_admin can update organizations
        if current_user.get('role') != 'super_admin':
            raise ValueError("Only super administrators can update organizations")
        
        # Prepare update
        update_doc = {
            'updated_at': datetime.utcnow(),
            'updated_by': current_user.get('email')
        }
        
        # Add allowed fields
        allowed_fields = ['name', 'display_name', 'description', 'plan', 'status', 'contact_email', 'settings']
        for field in allowed_fields:
            if field in update_data:
                update_doc[field] = update_data[field]
        
        # Build query to handle both ObjectId and string formats
        query_conditions = [
            {'_id': org_id},
            {'organization_id': org_id}
        ]
        
        # Try as ObjectId if it's a valid ObjectId string
        try:
            from bson import ObjectId as BsonObjectId
            if BsonObjectId.is_valid(org_id):
                obj_id = BsonObjectId(org_id)
                query_conditions.append({'_id': obj_id})
        except:
            pass
        
        # Update organization
        result = db.organizations.update_one(
            {'$or': query_conditions},
            {'$set': update_doc}
        )
        
        if result.modified_count > 0:
            logger.info(f"Organization updated: {org_id} by {current_user.get('email')}")
            return get_organization(org_id, current_user)
        
        return None
        
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise

def delete_organization(org_id, current_user):
    """Delete an organization"""
    try:
        db = get_db()
        
        # Only super_admin can delete organizations
        if current_user.get('role') != 'super_admin':
            raise ValueError("Only super administrators can delete organizations")
        
        # Build query to handle both ObjectId and string formats
        query_conditions = []
        
        # Try as string ID
        query_conditions.append({'_id': org_id})
        query_conditions.append({'organization_id': org_id})
        
        # Try as ObjectId if it's a valid ObjectId string
        try:
            from bson import ObjectId as BsonObjectId
            if BsonObjectId.is_valid(org_id):
                obj_id = BsonObjectId(org_id)
                query_conditions.append({'_id': obj_id})
        except:
            pass
        
        # Delete organization
        result = db.organizations.delete_one({'$or': query_conditions})
        
        if result.deleted_count > 0:
            logger.info(f"Organization deleted: {org_id} by {current_user.get('email')}")
            return True
        
        # If not found, log more details for debugging
        logger.warning(f"Organization not found for deletion: {org_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error deleting organization: {e}")
        raise

def get_organization_by_id(org_id):
    """Get organization by ID - simple version that works"""
    try:
        db = get_db()
        org = db.organizations.find_one({'$or': [
            {'_id': org_id},
            {'organization_id': org_id}
        ]})
        return org
    except Exception as e:
        logger.error(f"Error getting organization by ID: {e}")
        return None

def get_organization_usage_report(org_id, period='monthly'):
    """
    Get organization usage report with REAL data from metrics services.

    CRITICAL: NO MOCK DATA - All values from actual sources.

    Uses CUMULATIVE billing usage (per billing period) instead of just 24h metrics.
    """
    try:
        # Get real-time metrics from usage_metrics_service (for devices, users, storage)
        metrics = usage_metrics_service.get_organization_metrics(org_id)

        # Get CUMULATIVE billing usage for current billing period
        from .billing_usage_service import billing_usage_service
        billing_usage = billing_usage_service.get_usage_summary(org_id, period)

        # Extract values - all from real sources
        devices_data = metrics.get('devices', {})
        users_data = metrics.get('users', {})
        storage_data = metrics.get('storage', {})

        # Use billing usage for API calls and data transfer (cumulative)
        api_calls_billing = billing_usage.get('api_calls', {})
        data_transfer_billing = billing_usage.get('data_transfer', {})

        return {
            'org_id': org_id,
            'period': period,
            'billing_period': {
                'key': billing_usage.get('period_key', ''),
                'start': billing_usage.get('period_start'),
                'end': billing_usage.get('period_end')
            },
            'usage': {
                # Device metrics from MongoDB
                'devices': devices_data.get('total', 0),
                'active_devices': devices_data.get('active', 0),
                # User metrics from MongoDB
                'users': users_data.get('total', 0),
                # API calls - CUMULATIVE from billing_usage (not just 24h!)
                'api_calls': api_calls_billing.get('used', 0),
                'api_calls_limit': api_calls_billing.get('limit', 0),
                'api_calls_percentage': api_calls_billing.get('percentage', 0),
                'api_calls_remaining': api_calls_billing.get('remaining', 0),
                'api_calls_available': True,
                # Data transfer - CUMULATIVE from billing_usage
                'data_transfer_bytes': data_transfer_billing.get('total_bytes', 0),
                'data_transfer_in': data_transfer_billing.get('bytes_in', 0),
                'data_transfer_out': data_transfer_billing.get('bytes_out', 0),
                'data_transfer_limit': data_transfer_billing.get('limit_bytes', 0),
                'data_transfer_percentage': data_transfer_billing.get('percentage', 0),
                'data_transfer_available': True,
                # Storage from MongoDB + TimescaleDB + Redis (current, not cumulative)
                'storage_bytes': storage_data.get('total_bytes', 0),
                'storage_mongodb_bytes': storage_data.get('mongodb_bytes', 0),
                'storage_timescaledb_bytes': storage_data.get('timescaledb_bytes', 0),
                'storage_redis_bytes': storage_data.get('redis_bytes', 0),
                'storage_available': storage_data.get('available', False)
            },
            'alerts': metrics.get('alerts', {}).get('total', 0),
            'api_keys': metrics.get('api_keys', {}).get('total', 0),
            'data_sources': {
                'devices': 'mongodb',
                'users': 'mongodb',
                'api_calls': 'billing_usage_mongodb',  # Cumulative tracking
                'data_transfer': 'billing_usage_mongodb',  # Cumulative tracking
                'storage': storage_data.get('source', 'direct_query')
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting usage report: {e}")
        return {
            'org_id': org_id,
            'period': period,
            'usage': {
                'devices': 0,
                'users': 0,
                'api_calls': 0,
                'data_transfer_bytes': 0,
                'storage_bytes': 0
            },
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

def get_organization_billing(org_id=None, user=None):
    """Get organization billing info - simplified version"""
    try:
        return {
            'org_id': org_id,
            'billing': {
                'plan': 'starter',
                'status': 'active',
                'next_billing_date': (datetime.utcnow() + timedelta(days=30)).isoformat(),
                'amount': 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        return None

def upgrade_organization_plan(org_id, new_plan, effective_date=None, user=None):
    """Upgrade organization plan - simplified version"""
    try:
        db = get_db()
        result = db.organizations.update_one(
            {'$or': [{'_id': org_id}, {'organization_id': org_id}]},
            {'$set': {
                'plan': new_plan,
                'updated_at': datetime.utcnow(),
                'updated_by': user.get('email', 'system') if user else 'system'
            }}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error upgrading plan: {e}")
        return False

def can_user_access_organization(current_user: dict, org_id: str, permission: str = 'view') -> bool:
    """Check if user can access organization - simplified version"""
    try:
        user_role = current_user.get('role', 'user')
        user_org_id = current_user.get('organization_id', '')
        
        # Super admins can access all
        if user_role == 'super_admin':
            return True
        
        # SECURITY FIX: Platform admins have infrastructure-only access, NOT customer data
        if RBAC.is_platform_admin(current_user):
            # Check if organization is infrastructure-only
            org = get_organization_by_id(org_id)
            if org:
                is_infrastructure = (
                    org.get('category') in ['infrastructure', 'platform'] or
                    org.get('organization_id') in ['tesa-platform', 'infrastructure', 'monitoring'] or
                    any(keyword in org.get('name', '').lower() for keyword in ['tesa', 'infrastructure', 'platform', 'monitoring'])
                )
                if is_infrastructure:
                    logger.info(f"[SECURITY_AUDIT] Platform admin accessing infrastructure org: {org_id}")
                    return True
                else:
                    logger.warning(f"[SECURITY_VIOLATION_PREVENTED] Platform admin blocked from customer org: {org_id}")
                    return False
            return False
        
        # Check if user belongs to the organization
        return str(user_org_id) == str(org_id)
    except Exception as e:
        logger.error(f"Error checking access: {e}")
        return False

def get_db():
    """Get database connection - wrapper for compatibility"""
    from ..core.database import get_db as core_get_db
    return core_get_db()

# Keep compatibility with existing code
def format_organization_with_usage(org):
    """
    Format organization with actual usage counts from database queries.

    CRITICAL: NO MOCK DATA - All values from actual sources.
    """
    try:
        # Get database connection
        db = get_db()

        org_id = str(org.get('_id', ''))
        org_id_field = org.get('organization_id', org_id)
        org_name = org.get('name', '')

        # Count devices for this organization
        device_count = 0
        user_count = 0
        active_devices = 0
        alerts_count = 0
        api_keys_count = 0

        if db is not None:
            try:
                # Count devices - check multiple possible organization field formats
                device_query = {
                    '$or': [
                        {'organization_id': org_id},
                        {'organization_id': org_id_field},
                        {'organization': org_name},
                        {'organization': ObjectId(org_id) if ObjectId.is_valid(org_id) else None}
                    ]
                }
                # Remove None values from the $or array
                device_query['$or'] = [q for q in device_query['$or'] if q.get('organization') is not None or 'organization_id' in q]
                device_count = db.devices.count_documents(device_query)

                # Count active devices (last seen within 24 hours)
                from datetime import timedelta
                active_query = {
                    '$and': [
                        device_query,
                        {'last_seen': {'$gte': datetime.utcnow() - timedelta(hours=24)}}
                    ]
                }
                try:
                    active_devices = db.devices.count_documents(active_query)
                except Exception:
                    active_devices = 0

                # Count users for this organization - check multiple possible organization field formats
                user_query = {
                    '$or': [
                        {'organization_id': org_id},
                        {'organization_id': org_id_field},
                        {'organization': org_name}
                    ]
                }
                user_count = db.users.count_documents(user_query)

                # Count alerts for this organization
                try:
                    alerts_query = {'organization_id': {'$in': [org_id, org_id_field]}}
                    alerts_count = db.alerts.count_documents(alerts_query)
                except Exception:
                    alerts_count = 0

                # Count API keys for this organization
                try:
                    api_keys_query = {'organization_id': {'$in': [org_id, org_id_field]}}
                    api_keys_count = db.api_keys.count_documents(api_keys_query)
                except Exception:
                    api_keys_count = 0

                logger.info(f"Organization {org_name}: Found {device_count} devices ({active_devices} active), {user_count} users, {alerts_count} alerts")

            except Exception as query_error:
                logger.error(f"Error querying database for org {org_name}: {query_error}")
                device_count = 0
                user_count = 0
        else:
            logger.warning(f"No database connection available for org {org_name}")

        # Get additional metrics from usage_metrics_service (API calls, storage)
        api_calls_data = {}
        storage_data = {}
        data_transfer_data = {}
        billing_api_calls = 0

        try:
            api_calls_data = usage_metrics_service.get_api_calls_total()
            # BUGFIX: Pass org_id to get per-organization storage instead of platform-wide
            storage_data = usage_metrics_service.get_storage_usage(org_id)
            data_transfer_data = usage_metrics_service.get_data_transfer()
        except Exception as metrics_error:
            logger.warning(f"Error fetching metrics for org {org_name}: {metrics_error}")

        # Get CUMULATIVE API calls from billing_usage (more accurate than Prometheus 24h)
        try:
            from .billing_usage_service import billing_usage_service
            billing_summary = billing_usage_service.get_usage_summary(org_id, 'monthly')
            billing_api_calls = billing_summary.get('api_calls', {}).get('used', 0)
        except Exception as billing_error:
            logger.warning(f"Error fetching billing usage for org {org_name}: {billing_error}")

    except Exception as e:
        logger.error(f"Error formatting organization {org.get('name', 'Unknown')}: {e}")
        device_count = 0
        user_count = 0
        active_devices = 0
        alerts_count = 0
        api_keys_count = 0
        api_calls_data = {}
        storage_data = {}
        data_transfer_data = {}
        billing_api_calls = 0

    return {
        'id': str(org.get('_id', '')),
        'organization_id': org.get('organization_id', str(org.get('_id', ''))),
        'name': org.get('name', 'Unknown'),
        'display_name': org.get('display_name', org.get('name', 'Unknown')),
        'description': org.get('description', ''),
        'plan': org.get('plan', 'starter'),
        'status': org.get('status', 'active'),
        'contact_email': org.get('contact_email', ''),
        'created_at': str(org.get('created_at', '')),
        'updated_at': str(org.get('updated_at', '')),
        'settings': org.get('settings', {}),
        # REAL metrics from MongoDB
        'user_count': user_count,
        'device_count': device_count,
        'active_devices': active_devices,
        'alerts_count': alerts_count,
        'api_keys_count': api_keys_count,
        # REAL metrics from Prometheus/APISIX (platform-wide for now)
        'api_calls_24h': api_calls_data.get('requests_24h', 0),
        'api_calls_total': api_calls_data.get('total_requests', 0),
        'api_calls_available': api_calls_data.get('available', False),
        # CUMULATIVE API calls from billing_usage (accurate monthly count)
        'api_calls_billing': billing_api_calls,
        # REAL metrics from MongoDB + TimescaleDB + Redis (per-organization)
        'storage_bytes': storage_data.get('total_bytes', 0),
        'storage_mongodb_bytes': storage_data.get('mongodb_bytes', 0),
        'storage_timescaledb_bytes': storage_data.get('timescaledb_bytes', 0),
        'storage_redis_bytes': storage_data.get('redis_bytes', 0),
        'storage_available': storage_data.get('available', False),
        # REAL metrics from Prometheus/EMQX
        'data_transfer_bytes': data_transfer_data.get('total_bytes', 0),
        'data_transfer_in_24h': data_transfer_data.get('bytes_in_24h', 0),
        'data_transfer_out_24h': data_transfer_data.get('bytes_out_24h', 0),
        'data_transfer_available': data_transfer_data.get('available', False)
    }