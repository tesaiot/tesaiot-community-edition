/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Feature flags for controlling feature visibility and availability
 * These can be overridden by environment variables or backend configuration
 */
export interface FeatureFlags {
  // Core Features
  DEVICE_MANAGEMENT: boolean;
  TELEMETRY: boolean;
  USER_MANAGEMENT: boolean;
  ORGANIZATION_MANAGEMENT: boolean;

  // Telemetry Enhancements
  TELEMETRY_HISTORICAL_QUERY: boolean; // Enables /api/v1/telemetry/query rollup endpoint usage
  
  // Monitoring Features - Coming in v2025.07
  SYSTEM_HEALTH: boolean;
  ACTIVITY_LOGS: boolean;
  ANALYTICS: boolean;
  USAGE_ANALYTICS: boolean;
  
  // Extension Store Features - Coming in v2025.08
  EXTENSION_STORE: boolean;
  PKI_SERVICES: boolean;
  API_SERVICES: boolean;
  AI_ANALYTICS: boolean;
  DIGITAL_TWIN: boolean;
  INDUSTRIAL_IOT: boolean;
  
  // UI Features
  SHOW_COMING_SOON: boolean;
  SHOW_PREVIEW_FEATURES: boolean;
  ENABLE_DARK_MODE: boolean;
  
  // Development Features
  DEBUG_MODE: boolean;
  SHOW_DEV_TOOLS: boolean;

  // IoT Transport (preview)
  MQTT_QUIC_BUNDLE: boolean; // Show MQTT over QUIC + mTLS bundle option
}

/**
 * Default feature flags configuration
 */
export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  // Core Features - Already implemented
  DEVICE_MANAGEMENT: true,
  TELEMETRY: true,
  USER_MANAGEMENT: true,
  ORGANIZATION_MANAGEMENT: true,
  
  // Telemetry Enhancements
  TELEMETRY_HISTORICAL_QUERY: false,
  
  // Monitoring Features - Disabled until ready
  SYSTEM_HEALTH: false,
  ACTIVITY_LOGS: false,
  ANALYTICS: false,
  USAGE_ANALYTICS: false,
  
  // Extension Store Features - Enable when Extension Store is ready
  EXTENSION_STORE: false,
  PKI_SERVICES: false,
  API_SERVICES: false,
  AI_ANALYTICS: false,
  DIGITAL_TWIN: false,
  INDUSTRIAL_IOT: false,
  
  // UI Features
  SHOW_COMING_SOON: true,  // Show disabled menu items with "Coming Soon" badges
  SHOW_PREVIEW_FEATURES: false,  // Off for the Community Edition: preview features may surface out-of-scope capabilities
  ENABLE_DARK_MODE: false,
  
  // Development Features
  DEBUG_MODE: import.meta.env.DEV || false,
  SHOW_DEV_TOOLS: import.meta.env.DEV || false,

  // IoT Transport (preview)
  MQTT_QUIC_BUNDLE: false
};

/**
 * Load feature flags from environment variables
 * Environment variables should be prefixed with VITE_FEATURE_
 */
function loadFeatureFlagsFromEnv(): Partial<FeatureFlags> {
  const envFlags: Partial<FeatureFlags> = {};
  
  Object.keys(DEFAULT_FEATURE_FLAGS).forEach((key) => {
    const envKey = `VITE_FEATURE_${key}`;
    const envValue = import.meta.env[envKey];
    
    if (envValue !== undefined) {
      envFlags[key as keyof FeatureFlags] = envValue === 'true';
    }
  });
  
  return envFlags;
}

/**
 * Get the current feature flags configuration
 * Merges default flags with environment overrides
 */
export function getFeatureFlags(): FeatureFlags {
  const envFlags = loadFeatureFlagsFromEnv();
  
  return {
    ...DEFAULT_FEATURE_FLAGS,
    ...envFlags
  };
}

/**
 * Check if a specific feature is enabled
 */
export function isFeatureEnabled(feature: keyof FeatureFlags): boolean {
  const flags = getFeatureFlags();
  return flags[feature] || false;
}

/**
 * Get features by category
 */
export function getFeaturesByCategory() {
  const flags = getFeatureFlags();
  
  return {
    core: {
      deviceManagement: flags.DEVICE_MANAGEMENT,
      telemetry: flags.TELEMETRY,
      userManagement: flags.USER_MANAGEMENT,
      organizationManagement: flags.ORGANIZATION_MANAGEMENT
    },
    monitoring: {
      systemHealth: flags.SYSTEM_HEALTH,
      activityLogs: flags.ACTIVITY_LOGS
    },
    extensions: {
      store: flags.EXTENSION_STORE,
      pki: flags.PKI_SERVICES,
      api: flags.API_SERVICES,
      ai: flags.AI_ANALYTICS,
      digitalTwin: flags.DIGITAL_TWIN,
      industrialIoT: flags.INDUSTRIAL_IOT
    },
    ui: {
      showComingSoon: flags.SHOW_COMING_SOON,
      showPreview: flags.SHOW_PREVIEW_FEATURES,
      darkMode: flags.ENABLE_DARK_MODE
    },
    dev: {
      debug: flags.DEBUG_MODE,
      devTools: flags.SHOW_DEV_TOOLS
    }
  };
}

/**
 * Feature release timeline
 */
export const FEATURE_TIMELINE = {
  'v2025.06': ['DEVICE_MANAGEMENT', 'TELEMETRY', 'USER_MANAGEMENT', 'ORGANIZATION_MANAGEMENT'],
  'v2025.07': ['SYSTEM_HEALTH', 'ACTIVITY_LOGS'],
  'v2025.08': ['EXTENSION_STORE', 'PKI_SERVICES', 'API_SERVICES'],
  'v2025.09': ['AI_ANALYTICS', 'DIGITAL_TWIN'],
  'v2025.10': ['INDUSTRIAL_IOT']
};

/**
 * Get features available in a specific version
 */
export function getFeaturesForVersion(version: string): string[] {
  const features: string[] = [];
  const versions = Object.keys(FEATURE_TIMELINE).sort();
  
  for (const v of versions) {
    if (v <= version) {
      features.push(...FEATURE_TIMELINE[v as keyof typeof FEATURE_TIMELINE]);
    }
  }
  
  return features;
}

/**
 * Live device-log streaming requires a `/ws/device-logs/<id>` WebSocket backend
 * that the single-organization Community Edition does not ship. It is therefore
 * OFF by default — the Console tab shows a notice instead of opening a doomed
 * WebSocket. An Enterprise build can enable it with VITE_DEVICE_LOG_STREAMING=true.
 */
export const DEVICE_LOG_STREAMING_ENABLED =
  import.meta.env.VITE_DEVICE_LOG_STREAMING === 'true';
