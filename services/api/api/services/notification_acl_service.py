# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Notification ACL Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: v2025.06-beta
Module: Notification ACL Service
Description: Implements role-based access control for notifications
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, TEXT

from ..core.database import get_db

logger = logging.getLogger(__name__)

# Notification types by role visibility
NOTIFICATION_TYPES = {
    'system': {
        'visibility': ['super_admin'],
        'subtypes': ['platform_health', 'service_degradation', 'security_incident', 
                    'compliance_alert', 'license_expiry', 'resource_limit', 
                    'backup_status', 'update_available']
    },
    'ai_ml': {
        'visibility': ['super_admin', 'admin', 'org_admin', 'user', 'developer'],
        'subtypes': ['model_training_complete', 'anomaly_detected', 'predictive_maintenance',
                    'performance_optimization', 'model_accuracy_update', 'system_health_ai_alert',
                    'data_quality_issue', 'model_deployment', 'training_failure',
                    'inference_performance', 'drift_detected', 'retraining_required']
    },
    'org_health': {
        'visibility': ['super_admin', 'admin', 'org_admin'],
        'subtypes': ['quota_warning', 'billing_alert', 'user_limit', 
                    'device_limit', 'api_rate_limit', 'subscription_expiry']
    },
    'device': {
        'visibility': ['super_admin', 'admin', 'org_admin', 'user', 'developer', 'operator', 'viewer'],
        'subtypes': ['device_offline', 'device_online', 'telemetry_alert', 
                    'threshold_breach', 'maintenance_due', 'certificate_expiry', 
                    'certificate_issued', 'certificate_renewed', 'certificate_revoked',
                    'certificate_downloaded', 'firmware_update']
    },
    'user': {
        'visibility': ['super_admin', 'admin', 'org_admin', 'user', 'developer', 'operator', 'viewer'],
        'subtypes': ['login_alert', 'password_expiry', 'account_locked',
                    'permission_granted', 'permission_revoked', 'task_assigned',
                    'user_created', 'role_changed', 'user_deleted', 'password_reset']
    },
    'personal': {
        'visibility': ['super_admin', 'admin', 'org_admin', 'user', 'developer', 'operator', 'viewer'],
        'subtypes': ['reminder', 'task_update', 'mention', 'share', 'comment']
    },
    'security': {
        'visibility': ['super_admin', 'admin', 'org_admin'],
        'subtypes': ['unauthorized_access', 'suspicious_activity', 'api_abuse', 
                    'certificate_issue', 'authentication_failure']
    },
    'maintenance': {
        'visibility': ['super_admin', 'admin', 'org_admin'],
        'subtypes': ['scheduled_maintenance', 'emergency_maintenance', 
                    'service_update', 'feature_announcement']
    }
}

class NotificationACLService:
    """Service for managing notifications with ACL"""

    def __init__(self):
        self.db = None
        self._ensure_indexes()

    def _serialize_notification_for_client(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Convert notification document into JSON-serializable dict."""

        def _convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, ObjectId):
                return str(value)
            if isinstance(value, list):
                return [_convert(item) for item in value]
            if isinstance(value, dict):
                return {key: _convert(val) for key, val in value.items()}
            return value

        serialized = {key: _convert(val) for key, val in notification.items()}

        if '_id' in serialized:
            serialized['_id'] = str(serialized['_id'])
            serialized['id'] = serialized['_id']
        elif 'id' in serialized:
            serialized['id'] = str(serialized['id'])

        return serialized

    def _resolve_recipient_user_ids(self, notification: Dict[str, Any]) -> List[str]:
        """Determine concrete user recipients for real-time delivery."""

        try:
            db = self._get_db()
            if db is None:
                return []

            user_ids: Set[str] = set()

            recipient_type = notification.get('recipient_type')
            organization_id = notification.get('organization_id') or notification.get('recipient_id')

            # Direct user recipient
            if recipient_type == 'user' and notification.get('recipient_id'):
                user_ids.add(str(notification['recipient_id']))

            # Explicit list of recipients
            for recipient in notification.get('recipient_ids', []) or []:
                user_ids.add(str(recipient))

            # Role-targeted notifications
            if recipient_type == 'role' and notification.get('recipient_id'):
                query: Dict[str, Any] = {'role': notification['recipient_id']}
                if notification.get('organization_id'):
                    query['organization_id'] = notification['organization_id']
                for user in db.users.find(query, {'_id': 1}):
                    user_ids.add(str(user['_id']))

            # Organization-scoped notifications
            if recipient_type == 'organization' or notification.get('visibility_scope') == 'organization':
                if organization_id:
                    query = {'organization_id': organization_id}
                    allowed_roles = NOTIFICATION_TYPES.get(notification.get('type', ''), {}).get('visibility')
                    if allowed_roles:
                        query['role'] = {'$in': allowed_roles}
                    for user in db.users.find(query, {'_id': 1}):
                        user_ids.add(str(user['_id']))

            # System-wide notifications fall back to role visibility
            if notification.get('visibility_scope') == 'system':
                allowed_roles = NOTIFICATION_TYPES.get(notification.get('type', ''), {}).get('visibility', [])
                query: Dict[str, Any] = {}
                if allowed_roles:
                    query['role'] = {'$in': allowed_roles}
                for user in db.users.find(query, {'_id': 1}):
                    user_ids.add(str(user['_id']))

            return list(user_ids)

        except Exception as exc:
            logger.warning(f"Failed to resolve notification recipients: {exc}")
            return []

    def _broadcast_notification(self, notification: Dict[str, Any]) -> None:
        """Emit notification to connected WebSocket clients when possible."""

        try:
            from .websocket_service import websocket_service

            recipients = self._resolve_recipient_user_ids(notification)
            if recipients:
                websocket_service.send_notification(notification, recipient_ids=recipients)
            elif notification.get('visibility_scope') == 'system':
                # System notifications can be broadcast platform-wide
                websocket_service.send_notification(notification, recipient_ids=None)
        except Exception as exc:
            logger.debug(f"Skipping WebSocket notification broadcast due to error: {exc}")

    def _get_db(self):
        """Get database connection"""
        if self.db is not None:
            return self.db

        try:
            db = get_db()
            self.db = db
            return db
        except Exception:
            return None
    
    def _ensure_indexes(self):
        """Ensure all required indexes exist"""
        try:
            db = self._get_db()
            if db is None:
                return
            
            # Create indexes for performance
            indexes = [
                [("organization_id", ASCENDING), ("created_at", DESCENDING)],
                [("recipient_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
                [("recipient_ids", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
                [("type", ASCENDING), ("organization_id", ASCENDING), ("created_at", DESCENDING)],
                [("visibility_scope", ASCENDING), ("created_at", DESCENDING)],
                [("status", ASCENDING), ("archived", ASCENDING)],
                [("expires_at", ASCENDING)],
                [("organization_id", ASCENDING), ("recipient_type", ASCENDING), 
                 ("recipient_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]
            ]
            
            for index in indexes:
                db.notifications.create_index(index)
            
            # Create text index for search
            db.notifications.create_index([("title", TEXT), ("message", TEXT), ("keywords", TEXT)])
            
            # TTL index for auto-cleanup
            db.notifications.create_index("expires_at", expireAfterSeconds=0)
            
            logger.info("Notification indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def build_acl_query(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build MongoDB query based on user's role and permissions.
        
        Args:
            user: User object with role and organization info
            
        Returns:
            MongoDB query dict
        """
        user_id = str(user.get('_id', ''))
        user_role = user.get('role', 'user')
        organization_id = user.get('organization_id')
        
        # Super admin sees all notifications
        if user_role == 'super_admin':
            return {}
        
        # Build query conditions based on role
        conditions = []
        
        # Personal notifications
        conditions.append({
            'recipient_id': user_id,
            'recipient_type': 'user'
        })
        
        # Multiple recipient notifications
        conditions.append({
            'recipient_ids': user_id
        })
        
        # Role-based notifications within organization
        conditions.append({
            'recipient_id': user_role,
            'recipient_type': 'role',
            'organization_id': organization_id
        })
        
        # Organization admins see org-wide notifications
        if user_role in ['admin', 'org_admin']:
            conditions.append({
                'organization_id': organization_id,
                'visibility_scope': 'organization'
            })
        
        # Device notifications for assigned devices
        assigned_devices = user.get('assigned_devices', [])
        if assigned_devices:
            conditions.append({
                'type': 'device',
                'device_id': {'$in': assigned_devices},
                'organization_id': organization_id
            })
        
        return {'$or': conditions}
    
    def create_notification(self, notification_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new notification with proper ACL fields.
        
        Args:
            notification_data: Notification data dict
            
        Returns:
            Notification ID if created successfully
        """
        try:
            db = self._get_db()
            if db is None:
                return None

            # Validate notification type
            notif_type = notification_data.get('type')
            if notif_type not in NOTIFICATION_TYPES:
                raise ValueError(f"Invalid notification type: {notif_type}")
            
            # Set default values
            notification = {
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'status': 'unread',
                'archived': False,
                'read_by': [],
                **notification_data
            }
            
            # Set visibility scope based on type
            if 'visibility_scope' not in notification:
                if notification['type'] == 'system':
                    notification['visibility_scope'] = 'system'
                elif notification.get('recipient_type') == 'organization':
                    notification['visibility_scope'] = 'organization'
                else:
                    notification['visibility_scope'] = 'private'
            
            # Validate required fields
            if notification['visibility_scope'] != 'system' and not notification.get('organization_id'):
                raise ValueError('organization_id required for non-system notifications')
            
            # Validate recipient fields
            if not notification.get('recipient_id') and not notification.get('recipient_ids'):
                raise ValueError('Either recipient_id or recipient_ids must be specified')
            
            # Insert notification
            result = db.notifications.insert_one(notification)

            stored_notification = {**notification, '_id': result.inserted_id}
            serialized = self._serialize_notification_for_client(stored_notification)
            self._broadcast_notification(serialized)

            logger.info(f"Created notification {result.inserted_id} of type {notif_type}")
            return serialized['id']
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    def get_notifications(self, user: Dict[str, Any], filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get notifications for a user with ACL filtering.
        
        Args:
            user: User object
            filters: Additional filters (status, type, etc.)
            
        Returns:
            Dict with notifications and pagination info
        """
        try:
            db = self._get_db()
            if db is None:
                return {
                    'notifications': [],
                    'pagination': {
                        'total': 0,
                        'limit': filters.get('limit', 20) if filters else 20,
                        'offset': filters.get('offset', 0) if filters else 0,
                        'has_more': False
                    }
                }
            filters = filters or {}
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Combine with additional filters
            query = {**acl_query}
            
            # Add status filter
            if 'status' in filters and filters['status'] != 'all':
                query['status'] = filters['status']
            
            # Add type filter
            if 'type' in filters:
                query['type'] = filters['type']
            
            # Exclude archived by default
            if not filters.get('include_archived', False):
                query['archived'] = {'$ne': True}
            
            # Get pagination params
            limit = min(int(filters.get('limit', 20)), 100)
            offset = int(filters.get('offset', 0))
            
            # Execute query
            cursor = db.notifications.find(query).sort('created_at', DESCENDING)
            total = db.notifications.count_documents(query)
            
            # Apply pagination
            notifications = [
                self._serialize_notification_for_client(notif)
                for notif in cursor.skip(offset).limit(limit)
            ]

            seed_messages = {
                'User john.doe@example.com logged in from new location',
                'Device BMI270 #1 has been successfully registered',
                'Your account has been successfully set up. Explore the platform features.',
                'TESA IoT Platform v2025.06-beta-10 is available'
            }

            filtered_notifications = [
                notif for notif in notifications
                if notif.get('message') not in seed_messages
            ]

            removed_count = len(notifications) - len(filtered_notifications)
            if removed_count:
                notifications = filtered_notifications
                total = max(total - removed_count, 0)

            return {
                'notifications': notifications,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return {
                'notifications': [],
                'pagination': {
                    'total': 0,
                    'limit': 20,
                    'offset': 0,
                    'has_more': False
                }
            }

    def create_device_certificate_notification(
        self,
        *,
        event: str,
        device: Dict[str, Any],
        organization_id: str,
        actor: Optional[Dict[str, Any]] = None,
        priority: str = 'medium',
        metadata: Optional[Dict[str, Any]] = None,
        target_roles: Optional[List[str]] = None,
    ) -> List[Optional[str]]:
        """Create standardized notifications for device certificate events."""

        event_titles = {
            'certificate_issued': 'Device certificate issued',
            'certificate_renewed': 'Device certificate renewed',
            'certificate_revoked': 'Device certificate revoked',
            'certificate_downloaded': 'Certificate bundle downloaded',
            'certificate_expiry': 'Device certificate expiring soon',
        }

        event_messages = {
            'certificate_issued': 'Certificate generated for device {device_name}.',
            'certificate_renewed': 'Certificate renewed for device {device_name}.',
            'certificate_revoked': 'Certificate revoked for device {device_name}.',
            'certificate_downloaded': 'Certificate package downloaded for device {device_name}.',
            'certificate_expiry': 'Certificate for device {device_name} is nearing expiry.',
        }

        device_name = device.get('name') or device.get('device_id') or str(device.get('_id'))
        actor_email = actor.get('email') if actor else None
        actor_id = actor.get('_id') if actor else None

        metadata_payload: Dict[str, Any] = {
            **(metadata or {}),
            'device_id': device.get('device_id') or str(device.get('_id')),
            'device_name': device_name,
        }
        if actor_email:
            metadata_payload['actor'] = actor_email

        results: List[Optional[str]] = []
        roles = target_roles or ['admin', 'organization_admin']

        for role in roles:
            notification_data: Dict[str, Any] = {
                'type': 'device',
                'subtype': event,
                'title': event_titles.get(event, 'Device certificate event'),
                'message': event_messages.get(event, 'Device certificate event for {device_name}.').format(
                    device_name=device_name
                ),
                'priority': priority,
                'organization_id': organization_id,
                'recipient_type': 'role',
                'recipient_id': role,
                'device_id': device.get('device_id') or str(device.get('_id')),
                'device_name': device_name,
                'metadata': metadata_payload,
            }
            results.append(self.create_notification(notification_data))

        # Actor gets a personal notification for audit trail (when available)
        if actor_id:
            personal_notification = {
                'type': 'device',
                'subtype': event,
                'title': event_titles.get(event, 'Device certificate event'),
                'message': event_messages.get(event, 'Device certificate event for {device_name}.').format(
                    device_name=device_name
                ),
                'priority': priority,
                'organization_id': organization_id,
                'recipient_type': 'user',
                'recipient_id': str(actor_id),
                'visibility_scope': 'private',
                'device_id': device.get('device_id') or str(device.get('_id')),
                'device_name': device_name,
                'metadata': metadata_payload,
            }
            results.append(self.create_notification(personal_notification))

        return results

    def get_notification_by_id(self, user: Dict[str, Any], notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single notification by ID with ACL check.
        
        Args:
            user: User object
            notification_id: Notification ID
            
        Returns:
            Notification dict or None
        """
        try:
            db = self._get_db()
            if db is None:
                return None
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Add notification ID to query
            query = {
                '_id': ObjectId(notification_id),
                **acl_query
            }
            
            # Find notification
            notification = db.notifications.find_one(query)

            if notification:
                return self._serialize_notification_for_client(notification)

            return None
            
        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return None
    
    def update_notification_status(self, user: Dict[str, Any], notification_id: str, 
                                 status: str) -> bool:
        """
        Update notification status with ACL check.
        
        Args:
            user: User object
            notification_id: Notification ID
            status: New status ('read', 'unread', 'acknowledged', 'resolved')
            
        Returns:
            True if updated successfully
        """
        try:
            db = self._get_db()
            if db is None:
                return False
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Build update query
            query = {
                '_id': ObjectId(notification_id),
                **acl_query
            }
            
            # Build update data
            update_data = {
                '$set': {
                    'status': status,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
            
            # Add status-specific timestamps
            if status == 'read':
                update_data['$set']['read_at'] = datetime.now(timezone.utc)
                update_data['$addToSet'] = {
                    'read_by': {
                        'user_id': str(user['_id']),
                        'read_at': datetime.now(timezone.utc)
                    }
                }
            elif status == 'acknowledged':
                update_data['$set']['acknowledged_at'] = datetime.now(timezone.utc)
            elif status == 'resolved':
                update_data['$set']['resolved_at'] = datetime.now(timezone.utc)
            
            # Update notification
            result = db.notifications.update_one(query, update_data)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating notification status: {e}")
            return False
    
    def mark_all_as_read(self, user: Dict[str, Any]) -> int:
        """
        Mark all visible notifications as read for a user.
        
        Args:
            user: User object
            
        Returns:
            Number of notifications marked as read
        """
        try:
            db = self._get_db()
            if db is None:
                return 0
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Add unread filter
            query = {
                **acl_query,
                'status': 'unread',
                'archived': {'$ne': True}
            }
            
            # Update all matching notifications
            result = db.notifications.update_many(
                query,
                {
                    '$set': {
                        'status': 'read',
                        'read_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    },
                    '$addToSet': {
                        'read_by': {
                            'user_id': str(user['_id']),
                            'read_at': datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking all as read: {e}")
            return 0
    
    def get_unread_count(self, user: Dict[str, Any]) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user: User object
            
        Returns:
            Count of unread notifications
        """
        try:
            db = self._get_db()
            if db is None:
                return {
                    'by_status': {},
                    'by_type': {},
                    'by_severity': {},
                    'by_priority': {}
                }
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Count unread notifications
            count = db.notifications.count_documents({
                **acl_query,
                'status': 'unread',
                'archived': {'$ne': True}
            })
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def get_notification_stats(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get notification statistics for a user.
        
        Args:
            user: User object
            
        Returns:
            Statistics dict
        """
        try:
            db = self._get_db()
            if db is None:
                return False
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Run aggregation pipeline
            pipeline = [
                {'$match': acl_query},
                {
                    '$facet': {
                        'by_status': [
                            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
                        ],
                        'by_type': [
                            {'$group': {'_id': '$type', 'count': {'$sum': 1}}}
                        ],
                        'by_severity': [
                            {'$group': {'_id': '$severity', 'count': {'$sum': 1}}}
                        ],
                        'by_priority': [
                            {'$group': {'_id': '$priority', 'count': {'$sum': 1}}}
                        ]
                    }
                }
            ]
            
            result = list(db.notifications.aggregate(pipeline))
            
            if result:
                stats = result[0]
                
                # Convert to dict format
                return {
                    'by_status': {item['_id']: item['count'] for item in stats.get('by_status', [])},
                    'by_type': {item['_id']: item['count'] for item in stats.get('by_type', [])},
                    'by_severity': {item['_id']: item['count'] for item in stats.get('by_severity', [])},
                    'by_priority': {item['_id']: item['count'] for item in stats.get('by_priority', [])}
                }
            
            return {
                'by_status': {},
                'by_type': {},
                'by_severity': {},
                'by_priority': {}
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {
                'by_status': {},
                'by_type': {},
                'by_severity': {},
                'by_priority': {}
            }
    
    def archive_notification(self, user: Dict[str, Any], notification_id: str) -> bool:
        """
        Archive a notification with ACL check.
        
        Args:
            user: User object
            notification_id: Notification ID
            
        Returns:
            True if archived successfully
        """
        try:
            db = self._get_db()
            if db is None:
                return False
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Update notification
            result = db.notifications.update_one(
                {
                    '_id': ObjectId(notification_id),
                    **acl_query
                },
                {
                    '$set': {
                        'archived': True,
                        'archived_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error archiving notification: {e}")
            return False
    
    def delete_notification(self, user: Dict[str, Any], notification_id: str) -> bool:
        """
        Delete a notification with ACL check.
        
        Args:
            user: User object
            notification_id: Notification ID
            
        Returns:
            True if deleted successfully
        """
        try:
            db = self._get_db()
            if db is None:
                return False

            # Build ACL query
            acl_query = self.build_acl_query(user)

            # Delete notification
            result = db.notifications.delete_one({
                '_id': ObjectId(notification_id),
                **acl_query
            })
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False
    
    def search_notifications(self, user: Dict[str, Any], search_term: str, 
                           filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search notifications with full-text search and ACL filtering.
        
        Args:
            user: User object
            search_term: Search term
            filters: Additional filters
            
        Returns:
            Search results with pagination
        """
        try:
            db = self._get_db()
            filters = filters or {}
            
            # Build ACL query
            acl_query = self.build_acl_query(user)
            
            # Build search query
            query = {
                **acl_query,
                '$text': {'$search': search_term}
            }
            
            # Add additional filters
            if not filters.get('include_archived', False):
                query['archived'] = {'$ne': True}
            
            # Get pagination params
            limit = min(int(filters.get('limit', 20)), 100)
            offset = int(filters.get('offset', 0))
            
            # Execute search with text score
            cursor = db.notifications.find(
                query,
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'}), ('created_at', DESCENDING)])
            
            total = db.notifications.count_documents(query)
            
            # Apply pagination
            notifications = []
            for notif in cursor.skip(offset).limit(limit):
                serialized = self._serialize_notification_for_client(notif)
                serialized.pop('score', None)  # Remove text score from results if present
                notifications.append(serialized)
            
            return {
                'notifications': notifications,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                },
                'search_term': search_term
            }
            
        except Exception as e:
            logger.error(f"Error searching notifications: {e}")
            return {
                'notifications': [],
                'pagination': {
                    'total': 0,
                    'limit': 20,
                    'offset': 0,
                    'has_more': False
                },
                'search_term': search_term
            }


def create_notification_safe(notification_data: Dict[str, Any]) -> Optional[str]:
    """Helper to create notifications without raising exceptions upstream."""
    try:
        return notification_acl_service.create_notification(notification_data)
    except Exception as exc:
        logger.error(f"Failed to create notification safely: {exc}")
        return None


# Create singleton instance
notification_acl_service = NotificationACLService()
