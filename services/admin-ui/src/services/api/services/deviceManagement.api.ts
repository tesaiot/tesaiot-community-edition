/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Device Management API Service
 *
 * Handles all API operations for device CRUD and management
 * Extracted from tesaApi.ts (lines 549-657) as part of Phase 2 refactoring
 *
 * @module DeviceManagementApiService
 */

import { AxiosInstance } from 'axios';
import type {
  Device,
  GetDevicesParams,
  CreateDeviceRequest,
  UpdateDeviceRequest,
  ResetDevicePasswordResponse,
  ResetDevicePasswordRequest,
  RegenerateApiKeyResponse,
  RegenerateApiKeyRequest,
  DownloadServerTlsBundleOptions,
  DownloadErrorCallback,
  GetDeviceApiKeyInfoResponse,
  DeviceApiKeyInfo
} from '../types/deviceManagement.types';

/**
 * DeviceManagementApiService
 *
 * Provides methods for device lifecycle management:
 * - CRUD operations (create, read, update, delete)
 * - Security operations (password reset, API key regeneration)
 * - Bundle downloads (Server-TLS certificates and credentials)
 *
 * @example
 * ```typescript
 * const service = new DeviceManagementApiService(axiosInstance);
 * const devices = await service.getDevices({ organization: 'org-123' });
 * const device = await service.getDevice('device-456');
 * ```
 */
export class DeviceManagementApiService {
  constructor(private api: AxiosInstance) {}

  /**
   * Get all devices with optional filtering
   *
   * Handles different response structures from backend:
   * - Array directly
   * - Wrapped in { data: [...] }
   * - Wrapped in { devices: [...] }
   *
   * @param params - Optional query parameters (organization, etc.)
   * @returns Array of devices
   */
  async getDevices(params?: GetDevicesParams): Promise<Device[]> {
    const response = await this.api.get('/api/v1/devices/', { params });

    // Handle different response structures
    let devices: Device[] = [];
    if (Array.isArray(response.data)) {
      devices = response.data;
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      devices = response.data.data;
    } else if (response.data?.devices && Array.isArray(response.data.devices)) {
      devices = response.data.devices;
    } else {
      // Return empty array if structure is unexpected
      console.warn('Unexpected devices response structure:', response.data);
      return [];
    }

    // Ensure camelCase fields are populated from snake_case API response
    return devices.map(device => {
      if (device.trustm_uid && !device.trustmUid) {
        device.trustmUid = device.trustm_uid;
      }
      if (device.certificate_generation_method && !device.certificateGenerationMethod) {
        device.certificateGenerationMethod = device.certificate_generation_method;
      }
      if (device.generation_method && !device.generationMethod) {
        device.generationMethod = device.generation_method;
      }
      if (device.csr_provided !== undefined && device.csrProvided === undefined) {
        device.csrProvided = device.csr_provided;
      }
      return device;
    });
  }

  /**
   * Get single device by ID
   *
   * @param id - Device identifier
   * @returns Device details
   * @throws {AxiosError} If device not found (404) or other error
   */
  async getDevice(id: string): Promise<Device> {
    const response = await this.api.get(`/api/v1/devices/${id}`);
    const device = response.data;

    // Ensure camelCase fields are populated from snake_case API response
    // This ensures TypeScript code can use both naming conventions
    if (device.trustm_uid && !device.trustmUid) {
      device.trustmUid = device.trustm_uid;
    }
    if (device.certificate_generation_method && !device.certificateGenerationMethod) {
      device.certificateGenerationMethod = device.certificate_generation_method;
    }
    if (device.generation_method && !device.generationMethod) {
      device.generationMethod = device.generation_method;
    }
    if (device.csr_provided !== undefined && device.csrProvided === undefined) {
      device.csrProvided = device.csr_provided;
    }

    return device;
  }

  /**
   * Create new device
   *
   * @param device - Device data (without ID, auto-generated)
   * @returns Created device with ID
   * @throws {AxiosError} If validation fails or creation error
   */
  async createDevice(device: CreateDeviceRequest): Promise<Device> {
    const response = await this.api.post('/api/v1/devices/', device);
    return response.data;
  }

  /**
   * Update existing device
   *
   * Supports partial updates (only changed fields needed)
   *
   * @param id - Device identifier
   * @param device - Updated device data (partial)
   * @returns Updated device
   * @throws {AxiosError} If device not found or update fails
   */
  async updateDevice(id: string, device: UpdateDeviceRequest): Promise<Device> {
    const response = await this.api.put(`/api/v1/devices/${id}`, device);
    return response.data;
  }

  /**
   * Delete device by ID
   *
   * Permanently removes device from platform
   * WARNING: This action cannot be undone
   *
   * @param id - Device identifier
   * @throws {AxiosError} If device not found or deletion fails
   */
  async deleteDevice(id: string): Promise<void> {
    await this.api.delete(`/api/v1/devices/${id}`);
  }

  /**
   * Reset device MQTT password
   *
   * Generates new MQTT password for Server-TLS authentication
   * Password is returned ONCE in response (not retrievable later)
   *
   * SECURITY NOTE: Store the password immediately - it cannot be retrieved again
   *
   * @param deviceId - Device identifier
   * @param data - Optional: notify user, provide reason
   * @returns New MQTT credentials (username + password)
   * @throws {AxiosError} If device not found or reset fails
   */
  async resetDevicePassword(
    deviceId: string,
    data?: ResetDevicePasswordRequest
  ): Promise<ResetDevicePasswordResponse> {
    // New secure endpoint that returns password once in the same response
    const response = await this.api.post(
      `/api/v1/devices/${deviceId}/reset-mqtt-password`,
      data || {}
    );
    return response;
  }

  /**
   * Get device API key info (metadata only, no plaintext key)
   *
   * Returns API key metadata including:
   * - key_prefix: First part of key for identification (e.g., "tesaiot_dev_1e2f...")
   * - created_at: When the key was generated
   * - expires_at: When the key will expire
   * - last_used: Last time the key was used (null if never)
   * - usage_count: Number of times the key has been used
   *
   * NOTE: The actual API key is never returned - it was shown only once during creation
   *
   * @param deviceId - Device identifier
   * @returns API key metadata or null if no active key exists
   * @throws {AxiosError} If device not found or request fails
   */
  async getDeviceApiKeyInfo(deviceId: string): Promise<DeviceApiKeyInfo | null> {
    try {
      const response = await this.api.get<GetDeviceApiKeyInfoResponse>(
        `/api/v1/devices/${deviceId}/api-key`
      );
      return response.data?.api_key_info || null;
    } catch (error: any) {
      // 404 means no active API key - not an error condition
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Regenerate device API key
   *
   * Generates new API key for API-based authentication
   * Old key is immediately invalidated
   * New key is returned ONCE in response
   *
   * SECURITY NOTE: Store the API key immediately - it cannot be retrieved again
   *
   * @param deviceId - Device identifier
   * @param data - Optional: provide reason for audit trail
   * @returns New API key with metadata
   * @throws {AxiosError} If device not found or regeneration fails
   */
  async regenerateDeviceApiKey(
    deviceId: string,
    data?: RegenerateApiKeyRequest
  ): Promise<RegenerateApiKeyResponse> {
    const response = await this.api.post(
      `/api/v1/devices/${deviceId}/regenerate-api-key`,
      data || {}
    );
    return response;
  }

  /**
   * Download Server-TLS Complete Bundle (.zip)
   *
   * Downloads ZIP archive containing:
   * - CA certificate chain
   * - Server certificate
   * - Optional: MQTT password (if include_password=true)
   * - Optional: API key (if include_api_key=true)
   *
   * Supports two flavors:
   * - 'mqtt': For MQTT over Server-TLS (port 8884)
   * - 'https': For HTTPS REST API calls
   *
   * Browser automatically triggers download via blob URL
   *
   * @param deviceId - Device identifier
   * @param options - Download options (credentials, flavor)
   * @param onError - Optional error callback
   * @throws {Error} If download fails or device not found
   */
  async downloadServerTlsBundle(
    deviceId: string,
    options?: DownloadServerTlsBundleOptions,
    onError?: DownloadErrorCallback
  ): Promise<void> {
    const params: any = {};
    if (options?.include_password) params.include_password = 'true';
    if (options?.include_api_key) params.include_api_key = 'true';
    if (options?.flavor) params.flavor = options.flavor;

    try {
      const response = await this.api.get(
        `/api/v1/devices/${deviceId}/server-tls-bundle.zip`,
        {
          params,
          responseType: 'blob'
        }
      );

      // Derive filename from Content-Disposition or use fallback
      let filename = `${deviceId}-servertls-complete-bundle.zip`;
      const dispo = response.headers['content-disposition'] || response.headers['Content-Disposition'];
      if (dispo) {
        const match = /filename="?([^";]+)"?/i.exec(dispo);
        if (match && match[1]) filename = match[1];
      }

      // Create blob and trigger download
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      const code = err?.response?.status ?? 0;
      const msg = err?.response?.data?.message || err?.message || 'Download failed';
      if (onError) onError(code, msg);
      throw err;
    }
  }

  /**
   * Download MQTT-QUIC Server-TLS Bundle (.zip)
   *
   * Downloads ZIP archive containing:
   * - CA certificate chain
   * - MQTT-QUIC configuration JSON
   * - Optional: MQTT password (if include_password=true)
   * - Optional: API key (if include_api_key=true)
   *
   * For MQTT over QUIC transport (port 14567/UDP)
   *
   * Browser automatically triggers download via blob URL
   *
   * @param deviceId - Device identifier
   * @param options - Download options (credentials)
   * @param onError - Optional error callback
   * @throws {Error} If download fails or device not found
   */
  async downloadMqttQuicServerTlsBundle(
    deviceId: string,
    options?: { include_password?: boolean; include_api_key?: boolean },
    onError?: DownloadErrorCallback
  ): Promise<void> {
    const params: any = {};
    if (options?.include_password) params.include_password = 'true';
    if (options?.include_api_key) params.include_api_key = 'true';

    try {
      const response = await this.api.get(
        `/api/v1/devices/${deviceId}/mqtt-quic-server-tls-bundle.zip`,
        {
          params,
          responseType: 'blob'
        }
      );

      // Derive filename from Content-Disposition or use fallback
      let filename = `${deviceId}-mqttquic-servertls-complete-bundle.zip`;
      const dispo = response.headers['content-disposition'] || response.headers['Content-Disposition'];
      if (dispo) {
        const match = /filename="?([^";]+)"?/i.exec(dispo);
        if (match && match[1]) filename = match[1];
      }

      // Create blob and trigger download
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      const code = err?.response?.status ?? 0;
      const msg = err?.response?.data?.message || err?.message || 'MQTT-QUIC bundle download failed';
      if (onError) onError(code, msg);
      throw err;
    }
  }
}
