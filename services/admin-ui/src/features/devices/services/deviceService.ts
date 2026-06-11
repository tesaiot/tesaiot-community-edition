/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import authFetch from '@/utils/auth-fetch';
import { Device } from '../types/device.types';
import { DEVICE_API_ENDPOINTS } from '../constants/device.constants';

/**
 * Device service for all device-related API operations
 */
export class DeviceService {
  /**
   * Fetch all devices, optionally filtered by organization
   */
  async fetchDevices(organizationId?: string): Promise<Device[]> {
    let url = DEVICE_API_ENDPOINTS.LIST;
    if (organizationId) {
      url += `?organization=${organizationId}`;
    }

    const response = await authFetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch devices');
    }
    return response.json();
  }

  /**
   * Get devices with pagination and filtering options
   */
  async getDevices(options?: { limit?: number; offset?: number }): Promise<{ devices: Device[]; total: number }> {
    let url = DEVICE_API_ENDPOINTS.LIST;
    const params = new URLSearchParams();

    if (options?.limit) {
      params.append('limit', options.limit.toString());
    }
    if (options?.offset) {
      params.append('offset', options.offset.toString());
    }

    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    const response = await authFetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch devices');
    }

    const data = await response.json();
    // Handle both array response and paginated response
    if (Array.isArray(data)) {
      return { devices: data, total: data.length };
    }
    return { devices: data.devices || [], total: data.total || 0 };
  }

  /**
   * Create a new device
   */
  async createDevice(devicePayload: any): Promise<any> {
    const response = await authFetch(DEVICE_API_ENDPOINTS.CREATE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(devicePayload)
    });

    if (!response.ok) {
      throw new Error('Failed to create device');
    }
    return response.json();
  }

  /**
   * Update an existing device
   */
  async updateDevice(deviceId: string, updates: any): Promise<any> {
    // Log the update payload for debugging
    console.log('DeviceService: Updating device', deviceId, 'with payload:', updates);
    
    const response = await authFetch(DEVICE_API_ENDPOINTS.UPDATE(deviceId), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Failed to update device:', errorText);
      throw new Error('Failed to update device');
    }
    return response.json();
  }

  /**
   * Delete a device
   */
  async deleteDevice(deviceId: string): Promise<void> {
    const response = await authFetch(DEVICE_API_ENDPOINTS.DELETE(deviceId), {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error('Failed to delete device');
    }
  }

  /**
   * Generate certificate for a device
   */
  async generateCertificate(deviceId: string, certPayload?: any): Promise<any> {
    const response = await authFetch(DEVICE_API_ENDPOINTS.CERTIFICATE(deviceId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: certPayload ? JSON.stringify(certPayload) : undefined
    });

    if (!response.ok) {
      console.error('Failed to generate certificate for device');
      return null;
    }
    return response.json();
  }

  /**
   * Download certificate file
   */
  async downloadCertificate(deviceId: string, fileType: string): Promise<Blob> {
    // Use server-side 'bundle' endpoint directly (adds helper files)
    const response = await authFetch(`/api/v1/certificates/devices/${deviceId}/certificate/download/${fileType}`);
    
    if (!response.ok) {
      throw new Error(`Failed to download ${fileType}`);
    }
    return response.blob();
  }

  /**
   * Download certificate file but keep the raw Response (used for headers/metadata)
   */
  async downloadCertificateResponse(deviceId: string, fileType: string): Promise<Response> {
    const response = await authFetch(`/api/v1/certificates/devices/${deviceId}/certificate/download/${fileType}`);
    
    if (!response.ok) {
      throw new Error(`Failed to download ${fileType}`);
    }
    return response;
  }

  /**
   * Fetch device telemetry data
   */
  async fetchTelemetry(deviceId: string): Promise<any> {
    const response = await authFetch(DEVICE_API_ENDPOINTS.TELEMETRY(deviceId));
    
    if (!response.ok) {
      throw new Error('Failed to fetch telemetry');
    }
    return response.json();
  }

  /**
   * Bulk delete devices
   */
  async bulkDelete(deviceIds: string[]): Promise<void> {
    // Implement bulk delete if API supports it
    // For now, delete one by one
    const promises = deviceIds.map(id => this.deleteDevice(id));
    await Promise.all(promises);
  }

  /**
   * Export devices to CSV/JSON
   */
  async exportDevices(devices: Device[], format: 'csv' | 'json'): Promise<Blob> {
    if (format === 'csv') {
      // Convert to CSV
      const headers = ['Name', 'Type', 'Status', 'Serial Number', 'Organization', 'Last Seen'];
      const rows = devices.map(d => [
        d.name,
        d.type,
        d.status,
        d.serialNumber,
        d.organizationName,
        new Date(d.lastSeen).toISOString()
      ]);
      
      const csv = [headers, ...rows]
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n');
      
      return new Blob([csv], { type: 'text/csv' });
    } else {
      // Export as JSON
      return new Blob([JSON.stringify(devices, null, 2)], { type: 'application/json' });
    }
  }
}

// Export singleton instance
export const deviceService = new DeviceService();
