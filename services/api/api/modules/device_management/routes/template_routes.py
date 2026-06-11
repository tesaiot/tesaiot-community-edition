# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Template Routes

API endpoints for device template management
"""

from flask import Blueprint, request, jsonify, current_app
from fastapi import APIRouter
from functools import wraps
import logging
from typing import Dict, Any

from ....core.exceptions import ValidationError, ResourceNotFoundError, ConflictError

logger = logging.getLogger(__name__)

# Create FastAPI router for module integration
router = APIRouter(prefix="/templates", tags=["device-templates"])

# Create Flask blueprint for legacy support
template_bp = Blueprint('device_templates', __name__, url_prefix='/api/v1/device-templates')


# FastAPI endpoint for health check
@router.get("/health")
async def fastapi_health_check() -> Dict[str, Any]:
    """Health check endpoint for device templates (FastAPI)"""
    return {
        'status': 'healthy',
        'service': 'device-templates'
    }


def get_template_service():
    """Get template service from app context"""
    return current_app.template_service


def require_auth(f):
    """Authentication decorator (placeholder)"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # In production, implement proper authentication
        # For now, extract org_id and user_id from headers
        org_id = request.headers.get('X-Organization-ID', 'default_org')
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Add to kwargs
        kwargs['org_id'] = org_id
        kwargs['user_id'] = user_id
        
        return await f(*args, **kwargs)
    return decorated_function


@template_bp.route('/', methods=['POST'])
@require_auth
async def create_template(org_id: str, user_id: str):
    """Create a new device template"""
    try:
        template_service = get_template_service()
        data = request.get_json()
        
        template = await template_service.create_template(
            template_data=data,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>', methods=['GET'])
@require_auth
async def get_template(template_id: str, org_id: str, user_id: str):
    """Get a device template by ID"""
    try:
        template_service = get_template_service()
        
        template = await template_service.get_template(
            template_id=template_id,
            org_id=org_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        })
        
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>', methods=['PUT', 'PATCH'])
@require_auth
async def update_template(template_id: str, org_id: str, user_id: str):
    """Update a device template"""
    try:
        template_service = get_template_service()
        updates = request.get_json()
        
        template = await template_service.update_template(
            template_id=template_id,
            updates=updates,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        })
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>', methods=['DELETE'])
@require_auth
async def delete_template(template_id: str, org_id: str, user_id: str):
    """Delete (archive) a device template"""
    try:
        template_service = get_template_service()
        
        result = await template_service.delete_template(
            template_id=template_id,
            org_id=org_id
        )
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Template archived successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to archive template"
            }), 400
            
    except ConflictError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 409
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/', methods=['GET'])
@require_auth
async def list_templates(org_id: str, user_id: str):
    """List device templates with filtering and pagination"""
    try:
        template_service = get_template_service()
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        # Build filters
        filters = {}
        if 'status' in request.args:
            filters['status'] = request.args.get('status')
        if 'category' in request.args:
            filters['category'] = request.args.get('category')
        if 'device_type' in request.args:
            filters['device_type'] = request.args.get('device_type')
        if 'search' in request.args:
            filters['search'] = request.args.get('search')
        
        templates, total = await template_service.list_templates(
            org_id=org_id,
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            "status": "success",
            "templates": [t.to_dict() for t in templates],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>/instantiate', methods=['POST'])
@require_auth
async def instantiate_template(template_id: str, org_id: str, user_id: str):
    """Create a device from a template"""
    try:
        template_service = get_template_service()
        device_data = request.get_json()
        
        device = await template_service.instantiate_template(
            template_id=template_id,
            device_data=device_data,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "device": device.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error instantiating template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>/validate', methods=['POST'])
@require_auth
async def validate_template_data(template_id: str, org_id: str, user_id: str):
    """Validate data against a template"""
    try:
        template_service = get_template_service()
        data = request.get_json()
        
        result = await template_service.validate_template_data(
            template_id=template_id,
            data=data,
            org_id=org_id
        )
        
        return jsonify({
            "status": "success",
            "validation": result
        })
        
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error validating template data: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>/versions', methods=['GET'])
@require_auth
async def get_template_versions(template_id: str, org_id: str, user_id: str):
    """Get all versions of a template"""
    try:
        template_service = get_template_service()
        
        versions = await template_service.get_template_versions(
            template_id=template_id,
            org_id=org_id
        )
        
        return jsonify({
            "status": "success",
            "versions": [v.to_dict() for v in versions]
        })
        
    except Exception as e:
        logger.error(f"Error getting template versions: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>/versions/<version_number>', methods=['GET'])
@require_auth
async def get_template_version(template_id: str, version_number: str, org_id: str, user_id: str):
    """Get a specific version of a template"""
    try:
        template_service = get_template_service()
        
        version = await template_service.get_template_version(
            template_id=template_id,
            version_number=version_number,
            org_id=org_id
        )
        
        if version:
            return jsonify({
                "status": "success",
                "version": version.to_dict()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Version not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting template version: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/<template_id>/revert/<version_number>', methods=['POST'])
@require_auth
async def revert_template_version(template_id: str, version_number: str, org_id: str, user_id: str):
    """Revert a template to a previous version"""
    try:
        template_service = get_template_service()
        
        template = await template_service.revert_to_version(
            template_id=template_id,
            version_number=version_number,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        })
        
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error reverting template version: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/inherit', methods=['POST'])
@require_auth
async def inherit_template(org_id: str, user_id: str):
    """Create a new template that inherits from a parent"""
    try:
        template_service = get_template_service()
        data = request.get_json()
        
        parent_template_id = data.pop('parent_template_id', None)
        if not parent_template_id:
            return jsonify({
                "status": "error",
                "message": "parent_template_id is required"
            }), 400
        
        template = await template_service.inherit_template(
            parent_template_id=parent_template_id,
            child_template_data=data,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error inheriting template: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/compose', methods=['POST'])
@require_auth
async def compose_templates(org_id: str, user_id: str):
    """Create a new template by composing multiple templates"""
    try:
        template_service = get_template_service()
        data = request.get_json()
        
        template_ids = data.pop('template_ids', None)
        if not template_ids or not isinstance(template_ids, list):
            return jsonify({
                "status": "error",
                "message": "template_ids list is required"
            }), 400
        
        template = await template_service.compose_templates(
            template_ids=template_ids,
            composite_data=data,
            org_id=org_id,
            user_id=user_id
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except ResourceNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error composing templates: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/standards', methods=['GET'])
@require_auth
async def list_industry_standards(org_id: str, user_id: str):
    """List available industry standard templates"""
    try:
        template_service = get_template_service()
        
        standards = await template_service.list_industry_standards()
        
        return jsonify({
            "status": "success",
            "standards": standards
        })
        
    except Exception as e:
        logger.error(f"Error listing industry standards: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/standards/<standard_type>', methods=['POST'])
@require_auth
async def create_from_standard(standard_type: str, org_id: str, user_id: str):
    """Create a template from an industry standard"""
    try:
        template_service = get_template_service()
        customizations = request.get_json() or {}
        
        template = await template_service.create_industry_standard_template(
            standard_type=standard_type,
            org_id=org_id,
            user_id=user_id,
            customizations=customizations
        )
        
        return jsonify({
            "status": "success",
            "template": template.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating from standard: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@template_bp.route('/statistics', methods=['GET'])
@require_auth
async def get_template_statistics(org_id: str, user_id: str):
    """Get template usage statistics"""
    try:
        template_service = get_template_service()
        
        stats = await template_service.get_template_statistics(org_id)
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting template statistics: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500