/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * User Management API Service
 *
 * Handles all API operations for user CRUD and profile management
 * Extracted from tesaApi.ts (lines 621-678) as part of Phase 2 refactoring
 *
 * @module UserManagementApiService
 */

import { AxiosInstance } from 'axios';
import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UpdateProfileRequest,
  UpdateProfileResponse,
  ChangePasswordRequest,
  ChangePasswordResponse
} from '../types/userManagement.types';

/**
 * UserManagementApiService
 *
 * Provides methods for user lifecycle management:
 * - CRUD operations (create, read, update, delete)
 * - Profile management (update profile, change password)
 *
 * @example
 * ```typescript
 * const service = new UserManagementApiService(axiosInstance);
 * const users = await service.getUsers();
 * const user = await service.createUser({ username: 'john', email: 'john@example.com', ... });
 * ```
 */
export class UserManagementApiService {
  constructor(private api: AxiosInstance) {}

  /**
   * Get all users
   *
   * @returns Array of users
   * @throws {AxiosError} If request fails
   */
  async getUsers(): Promise<User[]> {
    const response = await this.api.get('/api/v1/users');
    return response.data;
  }

  /**
   * Create new user
   *
   * @param user - User data (without ID, auto-generated)
   * @returns Created user with ID
   * @throws {AxiosError} If validation fails or creation error
   */
  async createUser(user: CreateUserRequest): Promise<User> {
    const response = await this.api.post('/api/v1/users', user);
    return response.data;
  }

  /**
   * Update existing user
   *
   * Supports partial updates (only changed fields needed)
   *
   * @param id - User identifier
   * @param user - Updated user data (partial)
   * @returns Updated user
   * @throws {AxiosError} If user not found or update fails
   */
  async updateUser(id: string, user: UpdateUserRequest): Promise<User> {
    const response = await this.api.put(`/api/v1/users/${id}`, user);
    return response.data;
  }

  /**
   * Delete user by ID
   *
   * Permanently removes user from platform
   * WARNING: This action cannot be undone
   *
   * @param id - User identifier
   * @throws {AxiosError} If user not found or deletion fails
   */
  async deleteUser(id: string): Promise<void> {
    await this.api.delete(`/api/v1/users/${id}`);
  }

  /**
   * Update user profile
   *
   * Updates the current authenticated user's profile information
   *
   * @param profileData - Profile fields to update (partial)
   * @returns Update result with success flag and updated user data
   */
  async updateProfile(profileData: UpdateProfileRequest): Promise<UpdateProfileResponse> {
    try {
      const response = await this.api.put('/api/v1/auth/profile', profileData);
      // API may return the updated user directly or wrapped as { user }
      const user = (response.data && response.data.user) ? response.data.user : response.data;
      return { success: true, user };
    } catch (error) {
      console.error('Failed to update profile:', error);
      return { success: false };
    }
  }

  /**
   * Change user password
   *
   * Changes the current authenticated user's password
   * Requires current password for verification
   *
   * @param passwordData - Current and new password
   * @returns Change result with success flag and optional message
   */
  async changePassword(passwordData: ChangePasswordRequest): Promise<ChangePasswordResponse> {
    try {
      const response = await this.api.post('/api/v1/auth/change-password', passwordData);
      return { success: true, message: response.data.message };
    } catch (error) {
      console.error('Failed to change password:', error);
      return { success: false };
    }
  }
}
