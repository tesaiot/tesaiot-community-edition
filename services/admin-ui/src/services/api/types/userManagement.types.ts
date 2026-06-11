/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * User Management Types
 *
 * Type definitions for user CRUD operations and profile management
 * Extracted from tesaApi.ts as part of Phase 2 refactoring
 *
 * @module UserManagementTypes
 */

/**
 * User entity representing a platform user
 */
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'platform_admin' | 'organization_admin' | 'org_admin' | 'admin' | 'manager' | 'operator' | 'viewer' | 'user' | 'org_user';
  lastLogin?: string;
  isActive: boolean;
}

/**
 * User creation request (omits auto-generated fields)
 */
export type CreateUserRequest = Omit<User, 'id'>;

/**
 * User update request (partial fields allowed)
 */
export type UpdateUserRequest = Partial<User>;

/**
 * Profile update request data
 */
export interface UpdateProfileRequest {
  name?: string;
  email?: string;
  phone?: string;
  organization?: string;
  role?: string;
  avatar?: string;
}

/**
 * Profile update response
 */
export interface UpdateProfileResponse {
  success: boolean;
  user?: any;
}

/**
 * Password change request data
 */
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/**
 * Password change response
 */
export interface ChangePasswordResponse {
  success: boolean;
  message?: string;
}
