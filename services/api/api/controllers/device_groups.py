# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESAIoT Platform - Device Groups Controller

Implements Device Groups Management for targeted firmware deployments.
Supports 6 group types: SKU, Location, Environment, Customer, Firmware Version, Custom Tags.

Phase 6.1 of Secure OTA Service implementation.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, g, current_app
from bson import ObjectId

from ..core.auth import require_auth
from ..core.exceptions import (
    ValidationError,
    NotFoundError
)

# Create blueprint
device_groups_bp = Blueprint('device_groups', __name__, url_prefix='/api/v1')

# Valid group types
VALID_GROUP_TYPES = frozenset([
    'product_sku',      # Group by product SKU/model
    'location',         # Group by physical location
    'environment',      # Group by deployment environment
    'customer',         # Group by customer/tenant
    'firmware_version', # Group by current firmware version
    'custom'            # Custom tags
])

# Service instance (injected by app factory)
device_groups_service = None


def init_device_groups_controller(db):
    """Initialize Device Groups controller with database instance"""
    global device_groups_service
    device_groups_service = DeviceGroupsService(db)


class DeviceGroupsService:
    """Service for managing device groups"""

    def __init__(self, db):
        self.db = db

    def create_group(self, data: Dict, user_id: str, organization_id: str) -> Dict:
        """
        Create a new device group

        Args:
            data: Group data (name, type, criteria, etc.)
            user_id: User creating the group
            organization_id: Organization ID

        Returns:
            Created group record
        """
        # Validate required fields
        name = data.get('name', '').strip()
        group_type = data.get('type', '').strip()

        if not name:
            raise ValidationError('Group name is required')

        if len(name) > 100:
            raise ValidationError('Group name too long (max 100 chars)')

        if not group_type:
            raise ValidationError('Group type is required')

        if group_type not in VALID_GROUP_TYPES:
            raise ValidationError(f'Invalid group type. Valid types: {", ".join(VALID_GROUP_TYPES)}')

        # Check for duplicate name in organization
        existing = self.db.device_groups.find_one({
            'organization_id': organization_id,
            'name': {'$regex': f'^{re.escape(name)}$', '$options': 'i'}
        })

        if existing:
            raise ValidationError(f'Group with name "{name}" already exists')

        # Validate criteria based on type
        criteria = data.get('criteria', {})
        self._validate_criteria(group_type, criteria)

        # Create group record
        now = datetime.utcnow()
        group = {
            'organization_id': organization_id,
            'name': name,
            'description': data.get('description', '').strip()[:500],
            'type': group_type,
            'criteria': criteria,
            'device_count': 0,
            'auto_update': data.get('auto_update', True),
            'manual_members': [],
            'excluded_devices': [],
            'metadata': {
                'color': data.get('metadata', {}).get('color', '#7239ea'),
                'icon': data.get('metadata', {}).get('icon', 'folder')
            },
            'created_at': now,
            'created_by': user_id,
            'updated_at': now
        }

        result = self.db.device_groups.insert_one(group)
        group['_id'] = str(result.inserted_id)

        # Update device count based on criteria
        if group['auto_update']:
            group['device_count'] = self._count_matching_devices(group)

        return group

    def list_groups(self, organization_id: str, group_type: Optional[str] = None) -> List[Dict]:
        """List all device groups for an organization"""
        query = {'organization_id': organization_id}

        if group_type and group_type in VALID_GROUP_TYPES:
            query['type'] = group_type

        groups = list(self.db.device_groups.find(query).sort('name', 1))

        for group in groups:
            group['_id'] = str(group['_id'])

        return groups

    def get_group(self, group_id: str, organization_id: str) -> Dict:
        """Get a single device group by ID"""
        try:
            group = self.db.device_groups.find_one({
                '_id': ObjectId(group_id),
                'organization_id': organization_id
            })
        except Exception:
            raise NotFoundError('Invalid group ID format')

        if not group:
            raise NotFoundError('Device group not found')

        group['_id'] = str(group['_id'])
        return group

    def update_group(self, group_id: str, data: Dict, organization_id: str) -> Dict:
        """Update a device group"""
        # Verify group exists
        group = self.get_group(group_id, organization_id)

        update_fields = {}

        # Update name if provided
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                raise ValidationError('Group name cannot be empty')
            if len(name) > 100:
                raise ValidationError('Group name too long (max 100 chars)')

            # Check for duplicate name (exclude current group)
            existing = self.db.device_groups.find_one({
                '_id': {'$ne': ObjectId(group_id)},
                'organization_id': organization_id,
                'name': {'$regex': f'^{re.escape(name)}$', '$options': 'i'}
            })

            if existing:
                raise ValidationError(f'Group with name "{name}" already exists')

            update_fields['name'] = name

        # Update description
        if 'description' in data:
            update_fields['description'] = data['description'].strip()[:500]

        # Update type and criteria together
        if 'type' in data:
            group_type = data['type'].strip()
            if group_type not in VALID_GROUP_TYPES:
                raise ValidationError(f'Invalid group type. Valid types: {", ".join(VALID_GROUP_TYPES)}')
            update_fields['type'] = group_type

            # Criteria must be updated with type
            criteria = data.get('criteria', {})
            self._validate_criteria(group_type, criteria)
            update_fields['criteria'] = criteria
        elif 'criteria' in data:
            # Update criteria with existing type
            self._validate_criteria(group['type'], data['criteria'])
            update_fields['criteria'] = data['criteria']

        # Update auto_update
        if 'auto_update' in data:
            update_fields['auto_update'] = bool(data['auto_update'])

        # Update metadata
        if 'metadata' in data:
            update_fields['metadata'] = {
                'color': data['metadata'].get('color', group.get('metadata', {}).get('color', '#7239ea')),
                'icon': data['metadata'].get('icon', group.get('metadata', {}).get('icon', 'folder'))
            }

        if not update_fields:
            return group

        update_fields['updated_at'] = datetime.utcnow()

        self.db.device_groups.update_one(
            {'_id': ObjectId(group_id)},
            {'$set': update_fields}
        )

        return self.get_group(group_id, organization_id)

    def delete_group(self, group_id: str, organization_id: str) -> bool:
        """Delete a device group"""
        # Verify group exists
        self.get_group(group_id, organization_id)

        result = self.db.device_groups.delete_one({
            '_id': ObjectId(group_id),
            'organization_id': organization_id
        })

        return result.deleted_count > 0

    def get_group_devices(self, group_id: str, organization_id: str,
                          limit: int = 100, offset: int = 0) -> Dict:
        """Get devices in a group"""
        group = self.get_group(group_id, organization_id)

        # Build device query based on group criteria
        device_query = self._build_device_query(group)
        device_query['organization_id'] = organization_id

        # Get total count
        total = self.db.devices.count_documents(device_query)

        # Get devices with pagination
        devices = list(
            self.db.devices.find(device_query)
            .skip(offset)
            .limit(limit)
            .sort('created_at', -1)
        )

        for device in devices:
            device['_id'] = str(device['_id'])

        return {
            'devices': devices,
            'total': total,
            'limit': limit,
            'offset': offset
        }

    def add_devices_to_group(self, group_id: str, device_ids: List[str],
                             organization_id: str) -> Dict:
        """Manually add devices to a group"""
        group = self.get_group(group_id, organization_id)

        # Validate device IDs - support both UUID (device_id field) and ObjectId (_id field)
        valid_ids = []
        for device_id in device_ids:
            device = None
            # First try UUID format (device_id field)
            device = self.db.devices.find_one({
                'device_id': device_id,
                'organization_id': organization_id
            })
            # Then try ObjectId format (_id field)
            if not device:
                try:
                    if ObjectId.is_valid(device_id):
                        device = self.db.devices.find_one({
                            '_id': ObjectId(device_id),
                            'organization_id': organization_id
                        })
                except Exception:
                    pass
            if device:
                valid_ids.append(device_id)

        if not valid_ids:
            raise ValidationError('No valid device IDs provided')

        # Add to manual_members
        current_members = set(group.get('manual_members', []))
        current_members.update(valid_ids)

        # Remove from excluded_devices if present
        excluded = set(group.get('excluded_devices', []))
        excluded -= set(valid_ids)

        self.db.device_groups.update_one(
            {'_id': ObjectId(group_id)},
            {
                '$set': {
                    'manual_members': list(current_members),
                    'excluded_devices': list(excluded),
                    'updated_at': datetime.utcnow()
                }
            }
        )

        # Update device count
        updated_group = self.get_group(group_id, organization_id)
        device_count = self._count_matching_devices(updated_group)
        self.db.device_groups.update_one(
            {'_id': ObjectId(group_id)},
            {'$set': {'device_count': device_count}}
        )

        return {
            'added': len(valid_ids),
            'device_ids': valid_ids
        }

    def remove_devices_from_group(self, group_id: str, device_ids: List[str],
                                  organization_id: str) -> Dict:
        """Remove devices from a group"""
        group = self.get_group(group_id, organization_id)

        # Remove from manual_members
        current_members = set(group.get('manual_members', []))
        removed_from_manual = current_members.intersection(set(device_ids))
        current_members -= set(device_ids)

        # Add to excluded_devices
        excluded = set(group.get('excluded_devices', []))
        excluded.update(device_ids)

        self.db.device_groups.update_one(
            {'_id': ObjectId(group_id)},
            {
                '$set': {
                    'manual_members': list(current_members),
                    'excluded_devices': list(excluded),
                    'updated_at': datetime.utcnow()
                }
            }
        )

        # Update device count
        updated_group = self.get_group(group_id, organization_id)
        device_count = self._count_matching_devices(updated_group)
        self.db.device_groups.update_one(
            {'_id': ObjectId(group_id)},
            {'$set': {'device_count': device_count}}
        )

        return {
            'removed': len(device_ids),
            'device_ids': device_ids
        }

    def get_device_groups(self, device_id: str, organization_id: str) -> List[Dict]:
        """Get all groups a device belongs to"""
        try:
            device = self.db.devices.find_one({
                '_id': ObjectId(device_id),
                'organization_id': organization_id
            })
        except Exception:
            raise NotFoundError('Invalid device ID format')

        if not device:
            raise NotFoundError('Device not found')

        # Find groups where device is a member
        all_groups = list(self.db.device_groups.find({
            'organization_id': organization_id
        }))

        device_groups = []
        for group in all_groups:
            if self._device_in_group(device, group):
                group['_id'] = str(group['_id'])
                device_groups.append(group)

        return device_groups

    def _validate_criteria(self, group_type: str, criteria: Dict):
        """Validate criteria based on group type"""
        if group_type == 'product_sku':
            if not criteria.get('sku'):
                raise ValidationError('SKU is required for product_sku group type')

        elif group_type == 'location':
            if not (criteria.get('country') or criteria.get('region') or criteria.get('site')):
                raise ValidationError('At least one location field (country, region, site) is required')

        elif group_type == 'environment':
            if not criteria.get('environment'):
                raise ValidationError('Environment is required for environment group type')

        elif group_type == 'customer':
            if not criteria.get('customer_id'):
                raise ValidationError('Customer ID is required for customer group type')

        elif group_type == 'firmware_version':
            if not criteria.get('version_pattern'):
                raise ValidationError('Version pattern is required for firmware_version group type')

        elif group_type == 'custom':
            if not criteria.get('tags') or not isinstance(criteria['tags'], list):
                raise ValidationError('Tags list is required for custom group type')

    def _build_device_query(self, group: Dict) -> Dict:
        """Build MongoDB query for devices matching group criteria"""
        query = {'$or': []}

        # Manual members always included
        # Support both UUID (device_id field) and ObjectId (_id field) formats
        if group.get('manual_members'):
            member_ids = group['manual_members']
            # Separate UUIDs from ObjectIds
            uuid_ids = [id for id in member_ids if not ObjectId.is_valid(id)]
            objectid_ids = [id for id in member_ids if ObjectId.is_valid(id)]

            member_query = {'$or': []}
            if uuid_ids:
                member_query['$or'].append({'device_id': {'$in': uuid_ids}})
            if objectid_ids:
                member_query['$or'].append({'_id': {'$in': [ObjectId(id) for id in objectid_ids]}})

            if member_query['$or']:
                query['$or'].append(member_query)

        # Criteria-based query
        if group.get('auto_update', True):
            criteria = group.get('criteria', {})
            criteria_query = {}

            if group['type'] == 'product_sku':
                criteria_query['product_sku'] = criteria.get('sku')

            elif group['type'] == 'location':
                if criteria.get('country'):
                    criteria_query['location.country'] = criteria['country']
                if criteria.get('region'):
                    criteria_query['location.region'] = criteria['region']
                if criteria.get('site'):
                    criteria_query['location.site'] = criteria['site']

            elif group['type'] == 'environment':
                criteria_query['environment'] = criteria.get('environment')

            elif group['type'] == 'customer':
                criteria_query['customer_id'] = criteria.get('customer_id')

            elif group['type'] == 'firmware_version':
                pattern = criteria.get('version_pattern', '')
                if pattern:
                    # Convert glob pattern to regex
                    regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
                    criteria_query['firmware_version'] = {'$regex': f'^{regex_pattern}$'}

            elif group['type'] == 'custom':
                tags = criteria.get('tags', [])
                if tags:
                    criteria_query['tags'] = {'$in': tags}

            if criteria_query:
                query['$or'].append(criteria_query)

        # If no conditions, match nothing
        if not query['$or']:
            return {'_id': None}

        # Exclude devices in excluded_devices list
        # Support both UUID (device_id field) and ObjectId (_id field) formats
        if group.get('excluded_devices'):
            excluded_ids = group['excluded_devices']
            uuid_excluded = [id for id in excluded_ids if not ObjectId.is_valid(id)]
            objectid_excluded = [id for id in excluded_ids if ObjectId.is_valid(id)]

            exclude_conditions = []
            if uuid_excluded:
                exclude_conditions.append({'device_id': {'$nin': uuid_excluded}})
            if objectid_excluded:
                exclude_conditions.append({'_id': {'$nin': [ObjectId(id) for id in objectid_excluded]}})

            # Apply exclusions via $and to combine with existing query
            if exclude_conditions:
                if '$and' not in query:
                    query['$and'] = []
                query['$and'].extend(exclude_conditions)

        # Clean up query if only one $or condition
        if len(query['$or']) == 1:
            single_cond = query.pop('$or')[0]
            query.update(single_cond)
        elif not query['$or']:
            del query['$or']

        return query

    def _count_matching_devices(self, group: Dict) -> int:
        """Count devices matching group criteria"""
        query = self._build_device_query(group)
        query['organization_id'] = group['organization_id']
        return self.db.devices.count_documents(query)

    def _device_in_group(self, device: Dict, group: Dict) -> bool:
        """Check if a device belongs to a group"""
        # Check both _id (ObjectId as string) and device_id (UUID)
        device_object_id = str(device['_id'])
        device_uuid = device.get('device_id', '')

        # Check if excluded (match either _id or device_id)
        excluded = group.get('excluded_devices', [])
        if device_object_id in excluded or device_uuid in excluded:
            return False

        # Check if manual member (match either _id or device_id)
        manual_members = group.get('manual_members', [])
        if device_object_id in manual_members or device_uuid in manual_members:
            return True

        # Check criteria if auto_update enabled
        if group.get('auto_update', True):
            criteria = group.get('criteria', {})

            if group['type'] == 'product_sku':
                return device.get('product_sku') == criteria.get('sku')

            elif group['type'] == 'location':
                loc = device.get('location', {})
                if criteria.get('country') and loc.get('country') != criteria['country']:
                    return False
                if criteria.get('region') and loc.get('region') != criteria['region']:
                    return False
                if criteria.get('site') and loc.get('site') != criteria['site']:
                    return False
                return True

            elif group['type'] == 'environment':
                return device.get('environment') == criteria.get('environment')

            elif group['type'] == 'customer':
                return device.get('customer_id') == criteria.get('customer_id')

            elif group['type'] == 'firmware_version':
                pattern = criteria.get('version_pattern', '')
                if pattern:
                    regex = pattern.replace('.', r'\.').replace('*', '.*')
                    version = device.get('firmware_version', '')
                    return bool(re.match(f'^{regex}$', version))

            elif group['type'] == 'custom':
                device_tags = set(device.get('tags', []))
                group_tags = set(criteria.get('tags', []))
                return bool(device_tags.intersection(group_tags))

        return False


# ============================================================================
# API ENDPOINTS
# ============================================================================

@device_groups_bp.route('/device-groups', methods=['GET'])
@require_auth
def list_device_groups():
    """
    List all device groups for the organization

    Query Parameters:
        type: Filter by group type (optional)

    Returns:
        200: List of device groups
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        organization_id = g.current_user.get('organization_id')
        group_type = request.args.get('type')

        groups = device_groups_service.list_groups(organization_id, group_type)

        return jsonify({
            'groups': groups,
            'total': len(groups)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error listing device groups: {e}")
        return jsonify({'error': 'Failed to list device groups'}), 500


@device_groups_bp.route('/device-groups', methods=['POST'])
@require_auth
def create_device_group():
    """
    Create a new device group

    Request Body:
        name: Group name (required)
        type: Group type (required) - product_sku, location, environment, customer, firmware_version, custom
        description: Group description (optional)
        criteria: Group criteria based on type (required)
        auto_update: Auto-update membership (optional, default: true)
        metadata: UI metadata (color, icon) (optional)

    Returns:
        201: Created device group
        400: Validation error
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = g.current_user.get('_id') or g.current_user.get('user_id')
        organization_id = g.current_user.get('organization_id')

        group = device_groups_service.create_group(data, str(user_id), organization_id)

        return jsonify(group), 201

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating device group: {e}")
        return jsonify({'error': 'Failed to create device group'}), 500


@device_groups_bp.route('/device-groups/<group_id>', methods=['GET'])
@require_auth
def get_device_group(group_id):
    """
    Get a device group by ID

    Args:
        group_id: Device group ID

    Returns:
        200: Device group details
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        organization_id = g.current_user.get('organization_id')
        group = device_groups_service.get_group(group_id, organization_id)

        return jsonify(group), 200

    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting device group: {e}")
        return jsonify({'error': 'Failed to get device group'}), 500


@device_groups_bp.route('/device-groups/<group_id>', methods=['PATCH'])
@require_auth
def update_device_group(group_id):
    """
    Update a device group

    Args:
        group_id: Device group ID

    Request Body:
        name: Group name (optional)
        description: Group description (optional)
        type: Group type (optional)
        criteria: Group criteria (optional)
        auto_update: Auto-update membership (optional)
        metadata: UI metadata (optional)

    Returns:
        200: Updated device group
        400: Validation error
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        organization_id = g.current_user.get('organization_id')
        group = device_groups_service.update_group(group_id, data, organization_id)

        return jsonify(group), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error updating device group: {e}")
        return jsonify({'error': 'Failed to update device group'}), 500


@device_groups_bp.route('/device-groups/<group_id>', methods=['DELETE'])
@require_auth
def delete_device_group(group_id):
    """
    Delete a device group

    Args:
        group_id: Device group ID

    Returns:
        200: Group deleted successfully
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        organization_id = g.current_user.get('organization_id')
        device_groups_service.delete_group(group_id, organization_id)

        return jsonify({'message': 'Device group deleted successfully'}), 200

    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting device group: {e}")
        return jsonify({'error': 'Failed to delete device group'}), 500


@device_groups_bp.route('/device-groups/<group_id>/devices', methods=['GET'])
@require_auth
def get_group_devices(group_id):
    """
    Get devices in a group

    Args:
        group_id: Device group ID

    Query Parameters:
        limit: Maximum results (default: 100)
        offset: Pagination offset (default: 0)

    Returns:
        200: List of devices in group
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        organization_id = g.current_user.get('organization_id')
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))

        result = device_groups_service.get_group_devices(
            group_id, organization_id, limit, offset
        )

        return jsonify(result), 200

    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting group devices: {e}")
        return jsonify({'error': 'Failed to get group devices'}), 500


@device_groups_bp.route('/device-groups/<group_id>/devices', methods=['POST'])
@require_auth
def add_devices_to_group(group_id):
    """
    Add devices to a group

    Args:
        group_id: Device group ID

    Request Body:
        device_ids: List of device IDs to add

    Returns:
        200: Devices added
        400: Validation error
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        data = request.get_json()
        if not data or 'device_ids' not in data:
            return jsonify({'error': 'device_ids is required'}), 400

        organization_id = g.current_user.get('organization_id')
        result = device_groups_service.add_devices_to_group(
            group_id, data['device_ids'], organization_id
        )

        return jsonify(result), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error adding devices to group: {e}")
        return jsonify({'error': 'Failed to add devices to group'}), 500


@device_groups_bp.route('/device-groups/<group_id>/devices', methods=['DELETE'])
@require_auth
def remove_devices_from_group(group_id):
    """
    Remove devices from a group

    Args:
        group_id: Device group ID

    Request Body:
        device_ids: List of device IDs to remove

    Returns:
        200: Devices removed
        400: Validation error
        404: Group not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        data = request.get_json()
        if not data or 'device_ids' not in data:
            return jsonify({'error': 'device_ids is required'}), 400

        organization_id = g.current_user.get('organization_id')
        result = device_groups_service.remove_devices_from_group(
            group_id, data['device_ids'], organization_id
        )

        return jsonify(result), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error removing devices from group: {e}")
        return jsonify({'error': 'Failed to remove devices from group'}), 500


@device_groups_bp.route('/devices/<device_id>/groups', methods=['GET'])
@require_auth
def get_device_groups_endpoint(device_id):
    """
    Get all groups a device belongs to

    Args:
        device_id: Device ID

    Returns:
        200: List of groups
        404: Device not found
    """
    try:
        if not device_groups_service:
            return jsonify({'error': 'Device Groups service not available'}), 503

        organization_id = g.current_user.get('organization_id')
        groups = device_groups_service.get_device_groups(device_id, organization_id)

        return jsonify({
            'groups': groups,
            'total': len(groups)
        }), 200

    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting device groups: {e}")
        return jsonify({'error': 'Failed to get device groups'}), 500


@device_groups_bp.route('/device-groups/types', methods=['GET'])
@require_auth
def get_group_types():
    """
    Get available group types

    Returns:
        200: List of group types with descriptions
    """
    types = [
        {
            'value': 'product_sku',
            'label': 'Product SKU',
            'description': 'Group by product SKU or model number',
            'criteria_fields': ['sku']
        },
        {
            'value': 'location',
            'label': 'Location',
            'description': 'Group by physical location or region',
            'criteria_fields': ['country', 'region', 'site']
        },
        {
            'value': 'environment',
            'label': 'Environment',
            'description': 'Group by deployment environment',
            'criteria_fields': ['environment']
        },
        {
            'value': 'customer',
            'label': 'Customer',
            'description': 'Group by customer or tenant',
            'criteria_fields': ['customer_id']
        },
        {
            'value': 'firmware_version',
            'label': 'Firmware Version',
            'description': 'Group by current firmware version',
            'criteria_fields': ['version_pattern']
        },
        {
            'value': 'custom',
            'label': 'Custom Tags',
            'description': 'Group by custom tags',
            'criteria_fields': ['tags']
        }
    ]

    return jsonify({'types': types}), 200
