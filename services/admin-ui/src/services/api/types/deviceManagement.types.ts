/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Device Management Types
 *
 * Type definitions for device CRUD operations and management
 * Extracted from tesaApi.ts as part of Phase 2 refactoring
 *
 * @module DeviceManagementTypes
 */

/**
 * Device entity representing an IoT device in the platform
 */
export interface Device {
  id: string;
  _id?: string;
  device_id?: string;
  name: string;
  type: 'sensor' | 'actuator' | 'controller' | 'gateway' | string;
  status: 'active' | 'inactive' | 'error';
  lastSeen: string;
  last_seen?: string;
  location?: string;
  firmware?: string;
  firmware_version?: string;
  certificates?: any[]; // Certificate[] type will be in certificate module
  certificate_status?: string;
  organization_id?: string;
  metadata?: any;
  auth_mode?: 'mtls' | 'server_tls' | 'api_key';
  connection_status?: 'connected' | 'disconnected' | 'unknown';
  mqtt_username?: string;
  api_key?: string;
  created_at?: string;
  updated_at?: string;
  // Trust M fields (support both snake_case from API and camelCase for UI)
  trustm_uid?: string; // OPTIGA Trust M UID (27-byte hex, 54 chars) - snake_case from API
  trustmUid?: string; // OPTIGA Trust M UID - camelCase for UI compatibility
  certificate_generation_method?: string; // CSR detection field
  certificateGenerationMethod?: string; // camelCase variant
  generation_method?: string; // CSR detection field
  generationMethod?: string; // camelCase variant
  csr_provided?: boolean; // CSR detection field
  csrProvided?: boolean; // camelCase variant
}

/**
 * Parameters for fetching devices list
 */
export interface GetDevicesParams {
  organization?: string;
  status?: 'active' | 'inactive' | 'error';
  type?: string;
  limit?: number;
  offset?: number;
}

/**
 * Device creation request (omits auto-generated fields)
 */
export type CreateDeviceRequest = Omit<Device, 'id'>;

/**
 * Device update request (partial fields allowed)
 */
export type UpdateDeviceRequest = Partial<Device>;

/**
 * Response for device password reset operation
 */
export interface ResetDevicePasswordResponse {
  data: {
    success: boolean;
    device_id: string;
    mqtt_username: string;
    mqtt_password: string; // one-time view in response
    password_algorithm?: string;
    message: string;
  };
}

/**
 * Request parameters for device password reset
 */
export interface ResetDevicePasswordRequest {
  notify?: boolean;
  reason?: string;
}

/**
 * Response for device API key regeneration
 */
export interface RegenerateApiKeyResponse {
  data: {
    status: string;
    message: string;
    device_id: string;
    api_key: string;
    regenerated_at: string;
    note: string;
  };
}

/**
 * Request parameters for API key regeneration
 */
export interface RegenerateApiKeyRequest {
  reason?: string;
}

/**
 * Response for device API key info (metadata only, no plaintext key)
 */
export interface DeviceApiKeyInfo {
  key_id: string;
  device_id: string;
  key_prefix: string;
  created_at: string;
  expires_at: string;
  last_used: string | null;
  usage_count: number;
  permissions: string[];
}

/**
 * Response wrapper for device API key info
 */
export interface GetDeviceApiKeyInfoResponse {
  device_id: string;
  api_key_info: DeviceApiKeyInfo;
}

/**
 * Options for downloading Server-TLS bundle
 */
export interface DownloadServerTlsBundleOptions {
  include_password?: boolean;
  include_api_key?: boolean;
  flavor?: 'mqtt' | 'https';
}

/**
 * Error callback for download operations
 */
export type DownloadErrorCallback = (code: number, message: string) => void;
