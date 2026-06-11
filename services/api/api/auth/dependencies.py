# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..core.database import db_manager
from ..core.rbac import RBAC
from .models import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    FastAPI dependency to extract and validate JWT token

    Compatible with Flask-JWT-Extended tokens.
    This is a SYNC function - FastAPI will run it in a thread pool automatically.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User model with validated user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        # Decode JWT token (same secret as Flask-JWT-Extended)
        # Get JWT secret from environment variable
        secret_key = (
            os.environ.get('JWT_SECRET_KEY')
            or os.environ.get('JWT_SECRET')
            or os.environ.get('SECRET_KEY')
        )
        # SECURITY: Fail closed on any unset, placeholder, or weak/short secret.
        if (
            not secret_key
            or secret_key.startswith('CHANGEME')
            or len(secret_key) < 32
        ):
            logger.error("JWT secret is not configured or is too weak (CHANGEME*/<32 chars)")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server authentication is not configured",
            )

        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=['HS256']
            )
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Extract user info from token
        user_id = payload.get('user_id') or payload.get('sub')
        email = payload.get('email')
        role = payload.get('role', 'user')
        org_id = payload.get('organization_id')

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload (missing user_id or email)"
            )

        # Query user from MongoDB to get full info (sync call)
        if db_manager.mongo_db is not None:
            try:
                users_collection = db_manager.mongo_db['users']
                user_doc = users_collection.find_one({'_id': user_id})

                if user_doc:
                    return User(
                        id=str(user_doc['_id']),
                        email=user_doc.get('email'),
                        role=RBAC.canonicalize_role(user_doc.get('role')),
                        org_id=user_doc.get('organization_id'),
                        name=user_doc.get('name')
                    )
            except Exception as db_error:
                logger.warning(f"Failed to query user from DB: {db_error}")
                # Continue to fallback

        # Fallback: use token payload if DB unavailable or user not found
        return User(
            id=user_id,
            email=email,
            role=RBAC.canonicalize_role(role),
            org_id=org_id or 'unknown',
            name=payload.get('name') or email.split('@')[0]
        )

    except HTTPException:
        raise  # Re-raise HTTPException as-is

    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )
