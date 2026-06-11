# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Enhanced Device Logs Controller
Version: v2026.01
Build: 2026-01-09
Module: Device Logs Improvement Feature

Flask Blueprint for enhanced device logs with CSR workflow tracking.
"""

import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

from ..core.auth import require_auth
from ..core.database import db_manager

logger = logging.getLogger(__name__)

device_logs_bp = Blueprint('device_logs', __name__, url_prefix='/api/v1/devices')


# ============================================================
# Enhanced Device Logs Endpoints
# ============================================================

@device_logs_bp.route('/<device_id>/logs/enhanced', methods=['GET'])
@require_auth
def get_enhanced_device_logs(device_id: str):
    """
    Get enhanced device logs with filtering support.

    Query Parameters:
    - category: security, mqtt, csr, telemetry, command, system
    - level: TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL
    - source: device, platform, bridge, api
    - correlation_id: Correlation ID for distributed tracing
    - search: Regex search pattern
    - limit: Number of logs to return (default: 100, max: 1000)
    - skip: Number of logs to skip (default: 0)
    """
    try:
        # Parse query parameters
        category = request.args.get('category')
        level = request.args.get('level')
        source = request.args.get('source')
        correlation_id = request.args.get('correlation_id')
        search = request.args.get('search')
        limit = min(int(request.args.get('limit', 100)), 1000)
        skip = int(request.args.get('skip', 0))

        # Build MongoDB query
        query = {'device_id': device_id}

        if category:
            query['category'] = category
        if level:
            query['level'] = level
        if source:
            query['source'] = source
        if correlation_id:
            query['correlation_id'] = correlation_id
        if search:
            query['message'] = {'$regex': search, '$options': 'i'}

        # Query MongoDB
        mongo_db = db_manager.mongo_db
        logs_collection = mongo_db['enhanced_device_logs']

        logs_cursor = logs_collection.find(query).sort('timestamp', -1).skip(skip).limit(limit)
        logs = []

        for log in logs_cursor:
            log['_id'] = str(log['_id'])
            logs.append(log)

        total_count = logs_collection.count_documents(query)

        return jsonify({
            'logs': logs,
            'total': total_count,
            'limit': limit,
            'skip': skip,
            'device_id': device_id
        }), 200

    except Exception as e:
        logger.error(f"Error fetching enhanced device logs for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


@device_logs_bp.route('/<device_id>/logs/enhanced', methods=['POST'])
@require_auth
def add_enhanced_device_log(device_id: str):
    """
    Add a new enhanced device log entry.

    Request Body:
    {
        "category": "security|mqtt|csr|telemetry|command|system",
        "level": "TRACE|DEBUG|INFO|WARN|ERROR|CRITICAL",
        "source": "device|platform|bridge|api",
        "message": "Log message",
        "correlation_id": "optional-correlation-id",
        "metadata": { "key": "value" }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields
        required_fields = ['category', 'level', 'source', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create log entry
        log_entry = {
            'device_id': device_id,
            'category': data['category'],
            'level': data['level'],
            'source': data['source'],
            'message': data['message'],
            'correlation_id': data.get('correlation_id'),
            'metadata': data.get('metadata', {}),
            'timestamp': datetime.utcnow()
        }

        # Insert into MongoDB
        mongo_db = db_manager.mongo_db
        logs_collection = mongo_db['enhanced_device_logs']
        result = logs_collection.insert_one(log_entry)

        log_entry['_id'] = str(result.inserted_id)

        return jsonify({
            'success': True,
            'log_id': str(result.inserted_id),
            'log': log_entry
        }), 201

    except Exception as e:
        logger.error(f"Error adding enhanced device log for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


@device_logs_bp.route('/<device_id>/logs/enhanced/errors', methods=['GET'])
@require_auth
def get_device_error_logs(device_id: str):
    """Get all error and critical level logs for a device."""
    try:
        limit = min(int(request.args.get('limit', 100)), 1000)
        skip = int(request.args.get('skip', 0))

        mongo_db = db_manager.mongo_db
        logs_collection = mongo_db['enhanced_device_logs']

        query = {
            'device_id': device_id,
            'level': {'$in': ['ERROR', 'CRITICAL']}
        }

        logs_cursor = logs_collection.find(query).sort('timestamp', -1).skip(skip).limit(limit)
        logs = []

        for log in logs_cursor:
            log['_id'] = str(log['_id'])
            logs.append(log)

        total_count = logs_collection.count_documents(query)

        return jsonify({
            'errors': logs,
            'total': total_count,
            'limit': limit,
            'skip': skip,
            'device_id': device_id
        }), 200

    except Exception as e:
        logger.error(f"Error fetching error logs for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# CSR Workflow Status Endpoints
# ============================================================

@device_logs_bp.route('/<device_id>/csr-workflow/status', methods=['GET'])
@require_auth
def get_csr_workflow_status(device_id: str):
    """Get current CSR workflow status for a device."""
    try:
        mongo_db = db_manager.mongo_db
        workflow_collection = mongo_db['csr_workflow_status']

        workflow = workflow_collection.find_one({'device_id': device_id})

        if not workflow:
            return jsonify({
                'exists': False,
                'device_id': device_id,
                'message': 'No CSR workflow found for this device'
            }), 200

        workflow['_id'] = str(workflow['_id'])

        return jsonify({
            'exists': True,
            'workflow': workflow
        }), 200

    except Exception as e:
        logger.error(f"Error fetching CSR workflow status for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


@device_logs_bp.route('/<device_id>/csr-workflow/status', methods=['POST'])
@require_auth
def create_csr_workflow(device_id: str):
    """Create a new CSR workflow for a device."""
    try:
        data = request.get_json()

        mongo_db = db_manager.mongo_db
        workflow_collection = mongo_db['csr_workflow_status']

        # Check if workflow already exists
        existing = workflow_collection.find_one({'device_id': device_id})
        if existing:
            return jsonify({'error': 'CSR workflow already exists for this device'}), 409

        # Create workflow
        workflow = {
            'device_id': device_id,
            'current_step': 'mqtt_connected',
            'status': 'in_progress',
            'steps': {
                'mqtt_connected': {'status': 'completed', 'timestamp': datetime.utcnow()},
                'csr_submitted': {'status': 'pending'},
                'csr_validated': {'status': 'pending'},
                'certificate_signed': {'status': 'pending'},
                'certificate_delivered': {'status': 'pending'},
                'device_acknowledged': {'status': 'pending'}
            },
            'correlation_id': data.get('correlation_id'),
            'error_message': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = workflow_collection.insert_one(workflow)
        workflow['_id'] = str(result.inserted_id)

        return jsonify({
            'success': True,
            'workflow': workflow
        }), 201

    except Exception as e:
        logger.error(f"Error creating CSR workflow for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


@device_logs_bp.route('/<device_id>/csr-workflow/step', methods=['PUT'])
@require_auth
def update_csr_workflow_step(device_id: str):
    """
    Update CSR workflow step status.

    Request Body:
    {
        "step": "csr_submitted|csr_validated|certificate_signed|certificate_delivered|device_acknowledged",
        "status": "completed|failed|in_progress"
    }
    """
    try:
        data = request.get_json()

        if not data or 'step' not in data or 'status' not in data:
            return jsonify({'error': 'Missing required fields: step, status'}), 400

        step = data['step']
        status = data['status']

        mongo_db = db_manager.mongo_db
        workflow_collection = mongo_db['csr_workflow_status']

        # Update workflow
        update_data = {
            f'steps.{step}.status': status,
            f'steps.{step}.timestamp': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        if status == 'completed':
            update_data['current_step'] = step

        if status == 'failed':
            update_data['status'] = 'failed'
            update_data['error_message'] = data.get('error_message', 'Step failed')

        result = workflow_collection.update_one(
            {'device_id': device_id},
            {'$set': update_data}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Workflow not found'}), 404

        # Get updated workflow
        workflow = workflow_collection.find_one({'device_id': device_id})
        workflow['_id'] = str(workflow['_id'])

        return jsonify({
            'success': True,
            'workflow': workflow
        }), 200

    except Exception as e:
        logger.error(f"Error updating CSR workflow step for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500


@device_logs_bp.route('/csr-workflow/active', methods=['GET'])
@require_auth
def get_active_csr_workflows():
    """Get all active CSR workflows."""
    try:
        limit = min(int(request.args.get('limit', 50)), 500)
        skip = int(request.args.get('skip', 0))

        mongo_db = db_manager.mongo_db
        workflow_collection = mongo_db['csr_workflow_status']

        query = {'status': 'in_progress'}

        workflows_cursor = workflow_collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
        workflows = []

        for workflow in workflows_cursor:
            workflow['_id'] = str(workflow['_id'])
            workflows.append(workflow)

        total_count = workflow_collection.count_documents(query)

        return jsonify({
            'workflows': workflows,
            'total': total_count,
            'limit': limit,
            'skip': skip
        }), 200

    except Exception as e:
        logger.error(f"Error fetching active CSR workflows: {e}")
        return jsonify({'error': str(e)}), 500
