# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Device Routes
REST API endpoints for device management operations including bulk operations

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
from flask import Blueprint, request, jsonify, current_app

from ..models.bulk_models import (
    BulkCreateRequest, BulkUpdateRequest, BulkDeleteRequest,
    BulkOperationFilter, BulkOperationType, BulkOperationStatus
)
from ..models.query_models import DeviceQuery, QueryPagination
from ..services.device_service import ModularDeviceService
from ....auth.decorators import require_auth, require_permissions
from ...common.utils import get_client_info, validate_request_data
from ....core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

# Create blueprint
device_bp = Blueprint('devices', __name__, url_prefix='/api/v1/devices')


def get_device_service() -> ModularDeviceService:
    """Get device service instance"""
    return current_app.device_service


# Standard CRUD Operations

@device_bp.route('', methods=['POST'])
@require_auth
@require_permissions(['device:create'])
async def create_device():
    """Create a new device"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Validate required fields
        required_fields = ['name', 'device_type']
        validate_request_data(data, required_fields)
        
        # Get device service
        device_service = get_device_service()
        
        # Create device
        device = await device_service.register_device(
            device_data=data,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return jsonify({
            'status': 'success',
            'device': device
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating device: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/<device_id>', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def get_device(device_id: str):
    """Get device by ID"""
    try:
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get device service
        device_service = get_device_service()
        
        # Get device
        device = await device_service.get_device(
            device_id=device_id,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address']
        )
        
        if not device:
            raise NotFoundError(f"Device {device_id} not found")
        
        return jsonify({
            'status': 'success',
            'device': device
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/<device_id>', methods=['PUT', 'PATCH'])
@require_auth
@require_permissions(['device:update'])
async def update_device(device_id: str):
    """Update device"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get device service
        device_service = get_device_service()
        
        # Update device
        device = await device_service.update_device(
            device_id=device_id,
            updates=data,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return jsonify({
            'status': 'success',
            'device': device
        })
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error updating device {device_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/<device_id>', methods=['DELETE'])
@require_auth
@require_permissions(['device:delete'])
async def delete_device(device_id: str):
    """Delete device"""
    try:
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get device service
        device_service = get_device_service()
        
        # Delete device
        success = await device_service.delete_device(
            device_id=device_id,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        if not success:
            raise NotFoundError(f"Device {device_id} not found")
        
        return jsonify({
            'status': 'success',
            'message': f'Device {device_id} deleted successfully'
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error deleting device {device_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def list_devices():
    """List devices with filtering and pagination"""
    try:
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get query parameters
        filters = {}
        
        # Parse filters
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('device_type'):
            filters['device_type'] = request.args.get('device_type')
        if request.args.get('protocol'):
            filters['protocol'] = request.args.get('protocol')
        if request.args.get('tags'):
            filters['tags'] = request.args.get('tags').split(',')
        if request.args.get('search'):
            filters['$text'] = {'$search': request.args.get('search')}
        
        # Parse pagination
        pagination = {
            'page': int(request.args.get('page', 1)),
            'page_size': min(int(request.args.get('page_size', 20)), 100)
        }
        
        # Get device service
        device_service = get_device_service()
        
        # List devices
        devices = await device_service.list_devices(
            filters=filters,
            pagination=pagination,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address']
        )
        
        return jsonify({
            'status': 'success',
            'devices': devices,
            'pagination': pagination
        })
        
    except Exception as e:
        logger.error(f"Error listing devices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


# Bulk Operations

@device_bp.route('/bulk/create', methods=['POST'])
@require_auth
@require_permissions(['device:create', 'device:bulk'])
async def bulk_create_devices():
    """Bulk create devices"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Validate required fields
        required_fields = ['devices']
        validate_request_data(data, required_fields)
        
        # Create bulk request
        bulk_request = BulkCreateRequest(
            devices=data['devices'],
            provisioning_template_id=data.get('provisioning_template_id'),
            auto_generate_certificates=data.get('auto_generate_certificates', False),
            validate_only=data.get('validate_only', False),
            continue_on_error=data.get('continue_on_error', True),
            batch_size=data.get('batch_size', 100),
            metadata=data.get('metadata', {})
        )
        
        # Get device service
        device_service = get_device_service()
        
        # Initiate bulk create
        response = await device_service.bulk_create_devices(
            request=bulk_request,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return jsonify({
            'status': 'success',
            'bulk_operation': response.to_dict()
        }), 202  # Accepted
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error initiating bulk create: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/update', methods=['POST'])
@require_auth
@require_permissions(['device:update', 'device:bulk'])
async def bulk_update_devices():
    """Bulk update devices"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Validate required fields
        if not data.get('device_ids') and not data.get('filters'):
            raise ValidationError("Either device_ids or filters must be provided")
        if not data.get('updates'):
            raise ValidationError("Updates must be provided")
        
        # Create bulk request
        bulk_request = BulkUpdateRequest(
            device_ids=data.get('device_ids', []),
            updates=data['updates'],
            filters=data.get('filters'),
            validate_only=data.get('validate_only', False),
            continue_on_error=data.get('continue_on_error', True),
            batch_size=data.get('batch_size', 100),
            partial_update=data.get('partial_update', True),
            metadata=data.get('metadata', {})
        )
        
        # Get device service
        device_service = get_device_service()
        
        # Initiate bulk update
        response = await device_service.bulk_update_devices(
            request=bulk_request,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return jsonify({
            'status': 'success',
            'bulk_operation': response.to_dict()
        }), 202
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error initiating bulk update: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/delete', methods=['POST'])
@require_auth
@require_permissions(['device:delete', 'device:bulk'])
async def bulk_delete_devices():
    """Bulk delete devices"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Validate required fields
        if not data.get('device_ids') and not data.get('filters'):
            raise ValidationError("Either device_ids or filters must be provided")
        
        # Create bulk request
        bulk_request = BulkDeleteRequest(
            device_ids=data.get('device_ids', []),
            filters=data.get('filters'),
            force=data.get('force', False),
            delete_telemetry=data.get('delete_telemetry', False),
            delete_certificates=data.get('delete_certificates', False),
            validate_only=data.get('validate_only', False),
            continue_on_error=data.get('continue_on_error', True),
            batch_size=data.get('batch_size', 100),
            metadata=data.get('metadata', {})
        )
        
        # Get device service
        device_service = get_device_service()
        
        # Initiate bulk delete
        response = await device_service.bulk_delete_devices(
            request=bulk_request,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return jsonify({
            'status': 'success',
            'bulk_operation': response.to_dict()
        }), 202
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error initiating bulk delete: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/<operation_id>/progress', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def get_bulk_operation_progress(operation_id: str):
    """Get bulk operation progress"""
    try:
        user = request.current_user
        
        # Get device service
        device_service = get_device_service()
        
        # Get progress
        progress = await device_service.get_bulk_operation_progress(
            operation_id=operation_id,
            org_id=user['organization_id']
        )
        
        if not progress:
            raise NotFoundError(f"Operation {operation_id} not found")
        
        return jsonify({
            'status': 'success',
            'progress': progress.to_dict()
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting operation progress: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/<operation_id>/result', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def get_bulk_operation_result(operation_id: str):
    """Get bulk operation result"""
    try:
        user = request.current_user
        include_details = request.args.get('include_details', 'false').lower() == 'true'
        
        # Get device service
        device_service = get_device_service()
        
        # Get result
        result = await device_service.get_bulk_operation_result(
            operation_id=operation_id,
            org_id=user['organization_id'],
            include_details=include_details
        )
        
        if not result:
            raise NotFoundError(f"Operation {operation_id} not found")
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting operation result: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/<operation_id>/cancel', methods=['POST'])
@require_auth
@require_permissions(['device:update', 'device:bulk'])
async def cancel_bulk_operation(operation_id: str):
    """Cancel bulk operation"""
    try:
        user = request.current_user
        
        # Get device service
        device_service = get_device_service()
        
        # Cancel operation
        success = await device_service.cancel_bulk_operation(
            operation_id=operation_id,
            org_id=user['organization_id'],
            user=user
        )
        
        if not success:
            raise NotFoundError(f"Operation {operation_id} not found or already completed")
        
        return jsonify({
            'status': 'success',
            'message': f'Operation {operation_id} cancelled successfully'
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error cancelling operation: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/bulk/operations', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def list_bulk_operations():
    """List bulk operations"""
    try:
        user = request.current_user
        
        # Parse filters
        filter_params = BulkOperationFilter(
            operation_ids=request.args.getlist('operation_id'),
            operation_types=[BulkOperationType(t) for t in request.args.getlist('type')] if request.args.getlist('type') else None,
            statuses=[BulkOperationStatus(s) for s in request.args.getlist('status')] if request.args.getlist('status') else None,
            user_id=request.args.get('user_id'),
            organization_id=user['organization_id']
        )
        
        # Get device service
        device_service = get_device_service()
        
        # List operations
        operations = await device_service.list_bulk_operations(
            filter_params=filter_params,
            org_id=user['organization_id']
        )
        
        return jsonify({
            'status': 'success',
            'operations': operations
        })
        
    except Exception as e:
        logger.error(f"Error listing bulk operations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


# Device Status Operations

@device_bp.route('/<device_id>/status', methods=['GET'])
@require_auth
@require_permissions(['device:read'])
async def get_device_status(device_id: str):
    """Get device status"""
    try:
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get device service
        device_service = get_device_service()
        
        # Get status
        status = await device_service.get_device_status(
            device_id=device_id,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address']
        )
        
        return jsonify({
            'status': 'success',
            'device_status': status
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting device status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


@device_bp.route('/<device_id>/status', methods=['PUT'])
@require_auth
@require_permissions(['device:update'])
async def update_device_status(device_id: str):
    """Update device status"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Get device service
        device_service = get_device_service()
        
        # Update status
        success = await device_service.update_device_status(
            device_id=device_id,
            status=data,
            org_id=user['organization_id'],
            user=user,
            ip_address=client_info['ip_address']
        )
        
        if not success:
            raise NotFoundError(f"Device {device_id} not found")
        
        return jsonify({
            'status': 'success',
            'message': 'Device status updated successfully'
        })
        
    except NotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error updating device status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500


# Advanced Query Operations

@device_bp.route('/query', methods=['POST'])
@require_auth
@require_permissions(['device:read'])
async def query_devices():
    """Advanced device query"""
    try:
        data = request.get_json()
        user = request.current_user
        client_info = get_client_info(request)
        
        # Create query object
        query = DeviceQuery(
            org_id=user['organization_id'],
            device_types=data.get('device_types'),
            statuses=data.get('statuses'),
            protocols=data.get('protocols'),
            tags=data.get('tags'),
            created_date_range=data.get('created_date_range'),
            updated_date_range=data.get('updated_date_range'),
            last_seen_date_range=data.get('last_seen_date_range'),
            location_filter=data.get('location_filter'),
            text_search=data.get('text_search'),
            text_search_fields=data.get('text_search_fields', ['name', 'serial_number']),
            conditions=data.get('conditions'),
            pagination=QueryPagination(**data.get('pagination', {})),
            sort_options=data.get('sort_options'),
            options=data.get('options', {})
        )
        
        # Get device service
        device_service = get_device_service()
        
        # Execute query
        result = await device_service.query_devices(
            query=query,
            user=user,
            ip_address=client_info['ip_address']
        )
        
        return jsonify({
            'status': 'success',
            'result': result.to_dict()
        })
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error querying devices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500