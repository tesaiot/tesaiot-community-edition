/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Status color mappings for device status display
 */
export const DEVICE_STATUS_COLORS = {
  online: 'text-green-600',
  offline: 'text-gray-600',
  error: 'text-red-600',
  maintenance: 'text-yellow-600',
  default: 'text-gray-600'
} as const;

/**
 * Status background colors for badges and indicators
 */
export const DEVICE_STATUS_BG_COLORS = {
  online: 'bg-green-600',
  offline: 'bg-gray-400',
  error: 'bg-red-600',
  maintenance: 'bg-yellow-600'
} as const;

/**
 * Device type background colors
 */
export const DEVICE_TYPE_COLORS = {
  sensor: 'bg-blue-100 text-blue-600',
  actuator: 'bg-purple-100 text-purple-600',
  gateway: 'bg-green-100 text-green-600',
  controller: 'bg-gray-100 text-gray-600'
} as const;

/**
 * Default values for new device creation
 */
export const DEFAULT_NEW_DEVICE = {
  name: '',
  type: 'sensor' as const,
  serialNumber: '',
  organizationId: '',
  location: '',
  manufacturer: '',
  model: '',
  protocol: 'MQTTS' as const,
  tags: [] as string[],
  generateCertificate: true,
  certificateType: 'auto',
  certificateFormat: 'pem'
};

/**
 * Default firmware version for new devices
 */
export const DEFAULT_FIRMWARE_VERSION = '1.0.0';

/**
 * API endpoints
 */
export const DEVICE_API_ENDPOINTS = {
  BASE: '/api/v1/devices',
  LIST: '/api/v1/devices',
  CREATE: '/api/v1/devices',
  UPDATE: (id: string) => `/api/v1/devices/${id}`,
  DELETE: (id: string) => `/api/v1/devices/${id}`,
  TELEMETRY: (id: string) => `/api/v1/devices/${id}/telemetry`,
  CERTIFICATE: (id: string) => `/api/v1/certificates/devices/${id}/certificate`
} as const;

/**
 * Refresh intervals (in milliseconds)
 */
export const REFRESH_INTERVALS = {
  TELEMETRY: 15000, // 15 seconds - reduced from 1 second for lower server load
  REALTIME_TELEMETRY: 10000, // 10 seconds - for realtime dashboard
  DEVICE_LIST: 60000, // 1 minute
  AUTO_REFRESH: 15000 // 15 seconds - consistent with telemetry refresh
} as const;

/**
 * Filter options
 */
export const FILTER_OPTIONS = {
  ALL: 'all'
} as const;

/**
 * Toast messages
 */
export const TOAST_MESSAGES = {
  DEVICE_ADDED: (name: string) => `Device Added: ${name} has been successfully registered`,
  DEVICE_UPDATED: (name: string) => `Device Updated: ${name} has been updated`,
  DEVICE_DELETED: (name: string) => `Device Deleted: ${name} has been removed`,
  DEVICE_ERROR: 'Failed to perform device operation',
  CERTIFICATE_GENERATED: 'Certificate generated successfully',
  CERTIFICATE_ERROR: 'Failed to generate certificate'
} as const;

/**
 * Telemetry chart configuration
 */
export const TELEMETRY_CHART_DATA = {
  labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
  datasets: [{
    label: 'Messages/min',
    data: [100, 120, 115, 125, 130, 120, 125],
    borderColor: 'rgb(59, 130, 246)',
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    fill: true
  }]
};