# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):
    """
    User model compatible with Flask g.current_user structure

    Attributes:
        id: User ID (MongoDB ObjectId as string)
        email: User email address
        role: User role (admin, user, platform_admin, etc.)
        org_id: Organization ID (matches organization_id in Flask)
        name: Optional user name
    """

    id: str = Field(..., description="User ID (MongoDB ObjectId)")
    email: str = Field(..., description="User email address")
    role: str = Field(..., description="User role")
    org_id: str = Field(..., description="Organization ID", alias="organization_id")
    name: Optional[str] = Field(None, description="User display name")

    class Config:
        # Pydantic v1 uses 'allow_population_by_field_name' instead of v2's 'populate_by_name'
        allow_population_by_field_name = True  # Allow both org_id and organization_id

    @classmethod
    def from_flask_user(cls, flask_user: dict) -> "User":
        """
        Convert Flask g.current_user dict to FastAPI User model

        Args:
            flask_user: Dictionary from Flask g.current_user

        Returns:
            User model instance
        """
        return cls(
            id=flask_user.get('_id') or flask_user.get('id'),
            email=flask_user.get('email'),
            role=flask_user.get('role'),
            org_id=flask_user.get('organization_id'),
            name=flask_user.get('name')
        )
