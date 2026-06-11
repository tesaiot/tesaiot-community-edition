/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export type UUID = string;

// Language code type for user preferences
export type LanguageCode = 'en' | 'de' | 'es' | 'fr' | 'ja' | 'zh';

// Auth model representing the authentication session
export interface AuthModel {
  access_token: string;
  refresh_token?: string;
}

// User model representing the user profile
export interface UserModel {
  username: string;
  password?: string; // Optional as we don't always retrieve passwords
  email: string;
  first_name: string;
  last_name: string;
  fullname?: string; // May be stored directly in metadata
  email_verified?: boolean;
  occupation?: string;
  company_name?: string; // Using snake_case consistently
  phone?: string;
  roles?: number[]; // Array of role IDs
  pic?: string;
  language?: LanguageCode; // Maintain existing type
  is_admin?: boolean; // Added admin flag
  // Additional fields for TESA IoT Platform
  id?: string;
  name?: string;
  role?: 'platform_admin' | 'super_admin' | 'organization_admin' | 'admin' | 'user';
  organization_id?: string;
  organizationId?: string; // Add camelCase version for compatibility
  organization?: string;
  permissions?: Record<string, boolean>;
  created_at?: string;
}
