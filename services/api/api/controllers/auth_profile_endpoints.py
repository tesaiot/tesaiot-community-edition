# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Auth Profile Endpoints
Additional endpoints for user profile management
"""

from flask import Blueprint, request, jsonify, g
from api.core.auth import require_auth
from typing import Dict, Any, List
import logging
from datetime import datetime
import bcrypt
import hashlib
import os
from bson import ObjectId
from bson.errors import InvalidId
from ..core.database import get_db

logger = logging.getLogger(__name__)

# Create blueprint
auth_profile_bp = Blueprint('auth_profile', __name__)


def serialize_user(user: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if not user:
        return user

    result = {}
    for key, value in user.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_user(value)
        elif isinstance(value, list):
            result[key] = [serialize_user(item) if isinstance(item, dict) else str(item) if isinstance(item, ObjectId) else item for item in value]
        else:
            result[key] = value

    # Rename _id to id for consistency
    if '_id' in result:
        result['id'] = result.pop('_id')

    return result

# MongoDB connection - build from components to avoid URI parsing issues
MONGODB_HOST = os.getenv('MONGODB_HOST', 'tesa-mongodb')
MONGODB_PORT = os.getenv('MONGODB_PORT', '27017')
MONGODB_USER = os.getenv('MONGODB_USER', 'iot_user')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')
if not MONGODB_PASSWORD:
    raise RuntimeError('MONGODB_PASSWORD environment variable is required')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'tesa_iot')
MONGODB_AUTH_SOURCE = os.getenv('MONGODB_AUTH_SOURCE', 'admin')

# Build MongoDB URI from components
if MONGODB_USER and MONGODB_PASSWORD:
    MONGODB_URI = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DATABASE}?authSource={MONGODB_AUTH_SOURCE}"
else:
    MONGODB_URI = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DATABASE}"

# Do not get DB at import time; obtain within each request handler


def _build_user_lookup(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate MongoDB OR conditions to resolve the logged-in user reliably."""
    identifiers: List[Dict[str, Any]] = []

    # Email is the most stable identifier
    email = (current_user.get('email') or current_user.get('user_email'))
    if email:
        identifiers.append({'email': email.lower()})

    # Username (if assigned)
    username = current_user.get('username')
    if username:
        identifiers.append({'username': username})

    # Possible ID variants (_id, id, user_id)
    raw_ids = [current_user.get('_id'), current_user.get('id'), current_user.get('user_id')]
    for raw_id in raw_ids:
        if not raw_id:
            continue
        if isinstance(raw_id, ObjectId):
            identifiers.append({'_id': raw_id})
            continue
        try:
            identifiers.append({'_id': ObjectId(str(raw_id))})
        except (InvalidId, TypeError):
            logger.debug(f"auth_profile: invalid ObjectId value '{raw_id}' ignored")

    return identifiers


@auth_profile_bp.route('/api/v1/auth/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get current user profile"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection not available'}), 500
        current_user = g.current_user
        identifiers = _build_user_lookup(current_user)
        if not identifiers:
            logger.error("get_profile: unable to build identifiers for current user")
            return jsonify({'error': 'User context invalid'}), 401

        user = db.users.find_one({'$or': identifiers}, {'password_hash': 0, 'password': 0})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Serialize user to JSON-safe format (converts all ObjectIds, datetimes)
        user = serialize_user(user)

        # Maintain UI compatibility fields
        if user.get('avatar') and not user.get('pic'):
            user['pic'] = user['avatar']

        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500


@auth_profile_bp.route('/api/v1/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update current user profile"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection not available'}), 500
        current_user = g.current_user
        identifiers = _build_user_lookup(current_user)
        if not identifiers:
            logger.error("update_profile: unable to build identifiers for current user")
            return jsonify({'error': 'User context invalid'}), 401
        
        # Get update data
        data = request.get_json() or {}
        
        # Fields that can be updated (organization and email are excluded - read-only)
        # Email changes should go through a separate verification process
        allowed_fields = ['name', 'phone', 'department', 'position', 'avatar', 'avatar_url']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                # Normalize avatar_url into avatar for compatibility
                if field == 'avatar_url' and 'avatar' not in data:
                    update_data['avatar'] = data['avatar_url']
                else:
                    update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Add timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user in MongoDB using resolved identifiers
        result = db.users.update_one({'$or': identifiers}, {'$set': update_data})
        
        if result.modified_count == 0:
            return jsonify({'error': 'User not found or no changes made'}), 404
        
        # Get updated user
        user = db.users.find_one({'$or': identifiers}, {'password_hash': 0, 'password': 0})

        # Serialize user to JSON-safe format (converts all ObjectIds, datetimes)
        user = serialize_user(user)

        # Maintain UI compatibility fields
        if user.get('avatar') and not user.get('pic'):
            user['pic'] = user['avatar']

        resolved_user_id = (
            current_user.get('user_id')
            or (current_user.get('_id') and str(current_user['_id']))
            or current_user.get('email')
            or current_user.get('username')
            or 'unknown'
        )
        logger.info(f"Profile updated for user: {resolved_user_id}")
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500


@auth_profile_bp.route('/api/v1/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change current user password"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection not available'}), 500
        current_user = g.current_user
        user_id = current_user.get('_id') or current_user.get('user_id') or current_user.get('username')
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Validate new password strength
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        identifiers = _build_user_lookup(current_user)
        if not identifiers:
            logger.error("change_password: unable to resolve user context")
            return jsonify({'error': 'User context invalid'}), 401

        user = db.users.find_one({'$or': identifiers})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify current password
        password_verified = False
        password_hash = user.get('password_hash')
        legacy_hash = user.get('password')

        if password_hash:
            try:
                password_verified = bcrypt.checkpw(current_password.encode('utf-8'), password_hash.encode('utf-8'))
            except (ValueError, TypeError) as exc:
                logger.warning(f"change_password: bcrypt verification failed for user {user.get('email')}: {exc}")

        if not password_verified and legacy_hash:
            try:
                password_verified = hashlib.sha256(current_password.encode('utf-8')).hexdigest() == legacy_hash
            except Exception as exc:
                logger.error(f"change_password: legacy hash verification error for {user.get('email')}: {exc}")

        if not password_verified:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Hash new password
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password in MongoDB
        result = db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {
                    'password_hash': new_password_hash,
                    'password_updated_at': datetime.utcnow()
                },
                '$unset': {
                    'password': ""
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'Failed to update password'}), 500
        
        logger.info(f"Password changed for user: {user_id}")
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({'error': 'Failed to change password'}), 500
