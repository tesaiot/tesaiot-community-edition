/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// Device Health Status
export const DEVICE_HEALTH_STATUS = {
  HEALTHY: 'healthy',
  WARNING: 'warning',
  CRITICAL: 'critical',
  OFFLINE: 'offline'
} as const;

// Health Score Thresholds
export const HEALTH_SCORE_THRESHOLDS = {
  HEALTHY: 80,
  WARNING: 60,
  CRITICAL: 40
} as const;

// Device Log Levels
export const DEVICE_LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical'
} as const;

// Error Pattern Severity
export const ERROR_SEVERITY_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
} as const;

// Health Component Types
export const HEALTH_COMPONENTS = {
  CONNECTIVITY: 'connectivity',
  PERFORMANCE: 'performance',
  RELIABILITY: 'reliability',
  SECURITY: 'security'
} as const;

// Real-time Update Settings
export const DEVICE_HEALTH_SETTINGS = {
  WEBSOCKET_URL: (() => {
    const wsUrl = import.meta.env.VITE_DEVICE_HEALTH_WS_URL;
    if (wsUrl === 'auto' || !wsUrl) {
      // Auto-detect WebSocket URL based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      return `${protocol}//${host}/ws/device-health`;
    }
    return wsUrl;
  })(),
  RECONNECT_INTERVAL: 5000, // 5 seconds
  MAX_RECONNECT_ATTEMPTS: 5,
  HEARTBEAT_INTERVAL: 30000, // 30 seconds
  MAX_LOGS_IN_MEMORY: 500,
  UPDATE_BATCH_SIZE: 50,
  UPDATE_DEBOUNCE_MS: 100,
  TREND_DATA_POINTS: 24, // 24 hours of hourly data
  ERROR_PATTERN_LIMIT: 10
} as const;

// Dashboard Widget Settings
export const DEVICE_HEALTH_WIDGETS = {
  HEALTH_SCORE: {
    id: 'device-health-score',
    title: 'Device Health Score',
    refreshInterval: 10000
  },
  HEALTH_TRENDS: {
    id: 'device-health-trends',
    title: 'Health Trends',
    refreshInterval: 60000
  },
  ERROR_PATTERNS: {
    id: 'device-error-patterns',
    title: 'Error Pattern Detection',
    refreshInterval: 30000
  },
  DEVICE_LOGS: {
    id: 'device-logs',
    title: 'Device Logs',
    refreshInterval: 1000
  }
} as const;

// Health Score Colors
export const HEALTH_SCORE_COLORS = {
  [DEVICE_HEALTH_STATUS.HEALTHY]: {
    bg: 'bg-green-100 dark:bg-green-900/20',
    text: 'text-green-600 dark:text-green-400',
    border: 'border-green-200 dark:border-green-800'
  },
  [DEVICE_HEALTH_STATUS.WARNING]: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/20',
    text: 'text-yellow-600 dark:text-yellow-400',
    border: 'border-yellow-200 dark:border-yellow-800'
  },
  [DEVICE_HEALTH_STATUS.CRITICAL]: {
    bg: 'bg-red-100 dark:bg-red-900/20',
    text: 'text-red-600 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800'
  },
  [DEVICE_HEALTH_STATUS.OFFLINE]: {
    bg: 'bg-gray-100 dark:bg-gray-900/20',
    text: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-800'
  }
} as const;

// Export Types
export type DeviceHealthStatus = typeof DEVICE_HEALTH_STATUS[keyof typeof DEVICE_HEALTH_STATUS];
export type DeviceLogLevel = typeof DEVICE_LOG_LEVELS[keyof typeof DEVICE_LOG_LEVELS];
export type ErrorSeverityLevel = typeof ERROR_SEVERITY_LEVELS[keyof typeof ERROR_SEVERITY_LEVELS];
export type HealthComponent = typeof HEALTH_COMPONENTS[keyof typeof HEALTH_COMPONENTS];