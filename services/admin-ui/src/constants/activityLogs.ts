/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// Phase 1 Log Categories
export const PHASE1_LOG_CATEGORIES = {
  AUTH: 'auth',
  DEVICE: 'device',
  USER: 'user',
  SYSTEM: 'system',
  SECURITY: 'security',
  API: 'api',
  CONFIG: 'config',
  CERTIFICATE: 'certificate',
  OTA: 'ota',
  COMPLIANCE: 'compliance',
  INCIDENT: 'incident',
  DATA: 'data',
  // Device-specific categories
  DEVICE_CONNECTIVITY: 'device_connectivity',
  DEVICE_TELEMETRY: 'device_telemetry',
  DEVICE_HEALTH: 'device_health',
  DEVICE_SECURITY: 'device_security',
  DEVICE_FIRMWARE: 'device_firmware',
  DEVICE_CONFIGURATION: 'device_configuration',
  DEVICE_PERFORMANCE: 'device_performance'
} as const;

// Phase 1 Severity Levels
export const PHASE1_SEVERITY_LEVELS = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical'
} as const;

// Severity Colors for UI
export const SEVERITY_COLORS = {
  [PHASE1_SEVERITY_LEVELS.INFO]: {
    bg: 'bg-blue-100 dark:bg-blue-900/20',
    text: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-200 dark:border-blue-800',
    badge: 'secondary'
  },
  [PHASE1_SEVERITY_LEVELS.WARNING]: {
    bg: 'bg-amber-100 dark:bg-amber-900/20',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
    badge: 'warning'
  },
  [PHASE1_SEVERITY_LEVELS.ERROR]: {
    bg: 'bg-red-100 dark:bg-red-900/20',
    text: 'text-red-600 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800',
    badge: 'destructive'
  },
  [PHASE1_SEVERITY_LEVELS.CRITICAL]: {
    bg: 'bg-purple-100 dark:bg-purple-900/20',
    text: 'text-purple-600 dark:text-purple-400',
    border: 'border-purple-200 dark:border-purple-800',
    badge: 'destructive'
  }
} as const;

// WebSocket Event Types
export const WS_EVENT_TYPES = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  LOG_UPDATE: 'log:update',
  LOG_NEW: 'log:new',
  LOG_DELETE: 'log:delete',
  STATS_UPDATE: 'stats:update',
  CRITICAL_ALERT: 'alert:critical',
  SECURITY_ALERT: 'alert:security',
  SYSTEM_ALERT: 'alert:system',
  // Device-specific events
  DEVICE_LOG_NEW: 'device:log:new',
  DEVICE_CONNECTIVITY: 'device:connectivity',
  DEVICE_TELEMETRY: 'device:telemetry',
  DEVICE_HEALTH_UPDATE: 'device:health:update',
  DEVICE_ERROR: 'device:error'
} as const;

// Filter Presets
export const FILTER_PRESETS = {
  CRITICAL_ONLY: {
    name: 'Critical Events',
    severity: [PHASE1_SEVERITY_LEVELS.CRITICAL],
    timeRange: '24h'
  },
  SECURITY_AUDIT: {
    name: 'Security Audit',
    category: [PHASE1_LOG_CATEGORIES.SECURITY, PHASE1_LOG_CATEGORIES.AUTH],
    severity: [PHASE1_SEVERITY_LEVELS.WARNING, PHASE1_SEVERITY_LEVELS.ERROR, PHASE1_SEVERITY_LEVELS.CRITICAL],
    timeRange: '7d'
  },
  RECENT_ERRORS: {
    name: 'Recent Errors',
    severity: [PHASE1_SEVERITY_LEVELS.ERROR, PHASE1_SEVERITY_LEVELS.CRITICAL],
    timeRange: '1h'
  },
  USER_ACTIVITY: {
    name: 'User Activity',
    category: [PHASE1_LOG_CATEGORIES.USER, PHASE1_LOG_CATEGORIES.AUTH],
    timeRange: '24h'
  },
  SYSTEM_HEALTH: {
    name: 'System Health',
    category: [PHASE1_LOG_CATEGORIES.SYSTEM, PHASE1_LOG_CATEGORIES.API],
    timeRange: '1h'
  },
  // Device-specific presets
  DEVICE_ISSUES: {
    name: 'Device Issues',
    category: [
      PHASE1_LOG_CATEGORIES.DEVICE_CONNECTIVITY,
      PHASE1_LOG_CATEGORIES.DEVICE_HEALTH,
      PHASE1_LOG_CATEGORIES.DEVICE_PERFORMANCE
    ],
    severity: [PHASE1_SEVERITY_LEVELS.WARNING, PHASE1_SEVERITY_LEVELS.ERROR, PHASE1_SEVERITY_LEVELS.CRITICAL],
    timeRange: '24h'
  },
  DEVICE_SECURITY: {
    name: 'Device Security',
    category: [
      PHASE1_LOG_CATEGORIES.DEVICE_SECURITY,
      PHASE1_LOG_CATEGORIES.CERTIFICATE
    ],
    severity: [PHASE1_SEVERITY_LEVELS.WARNING, PHASE1_SEVERITY_LEVELS.ERROR, PHASE1_SEVERITY_LEVELS.CRITICAL],
    timeRange: '7d'
  },
  DEVICE_TELEMETRY: {
    name: 'Device Telemetry',
    category: [PHASE1_LOG_CATEGORIES.DEVICE_TELEMETRY],
    timeRange: '1h'
  },
  ALL_DEVICE_LOGS: {
    name: 'All Device Logs',
    category: [
      PHASE1_LOG_CATEGORIES.DEVICE,
      PHASE1_LOG_CATEGORIES.DEVICE_CONNECTIVITY,
      PHASE1_LOG_CATEGORIES.DEVICE_TELEMETRY,
      PHASE1_LOG_CATEGORIES.DEVICE_HEALTH,
      PHASE1_LOG_CATEGORIES.DEVICE_SECURITY,
      PHASE1_LOG_CATEGORIES.DEVICE_FIRMWARE,
      PHASE1_LOG_CATEGORIES.DEVICE_CONFIGURATION,
      PHASE1_LOG_CATEGORIES.DEVICE_PERFORMANCE
    ],
    timeRange: '24h'
  }
} as const;

// Real-time Update Settings
export const REALTIME_SETTINGS = {
  WEBSOCKET_URL: (() => {
    const wsUrl = import.meta.env.VITE_WS_URL;
    if (wsUrl === 'auto') {
      // Auto-detect WebSocket URL based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      return `${protocol}//${host}/ws`;
    }
    // Fallback to current host if no wsUrl provided
    if (!wsUrl) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      return `${protocol}//${host}/ws`;
    }
    return wsUrl;
  })(),
  RECONNECT_INTERVAL: 5000, // 5 seconds
  MAX_RECONNECT_ATTEMPTS: 5,
  HEARTBEAT_INTERVAL: 30000, // 30 seconds
  MAX_LOGS_IN_MEMORY: 1000,
  UPDATE_BATCH_SIZE: 50,
  UPDATE_DEBOUNCE_MS: 100
} as const;

// Dashboard Widget Settings
export const DASHBOARD_WIDGETS = {
  CRITICAL_MONITOR: {
    id: 'critical-monitor',
    title: 'Critical Events Monitor',
    refreshInterval: 5000,
    maxItems: 5
  },
  SECURITY_ALERTS: {
    id: 'security-alerts',
    title: 'Security Alerts',
    refreshInterval: 10000,
    maxItems: 10
  },
  ACTIVITY_TIMELINE: {
    id: 'activity-timeline',
    title: 'Real-time Activity',
    refreshInterval: 1000,
    maxItems: 20
  },
  STATS_OVERVIEW: {
    id: 'stats-overview',
    title: 'Statistics Overview',
    refreshInterval: 30000
  }
} as const;

// Export Types
export type LogCategory = typeof PHASE1_LOG_CATEGORIES[keyof typeof PHASE1_LOG_CATEGORIES];
export type SeverityLevel = typeof PHASE1_SEVERITY_LEVELS[keyof typeof PHASE1_SEVERITY_LEVELS];
export type WSEventType = typeof WS_EVENT_TYPES[keyof typeof WS_EVENT_TYPES];