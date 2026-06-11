/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export type LicenseEdition = 'community' | 'startup' | 'business' | 'enterprise';

export interface LicenseLimits {
  devices: number;
  users: number;
  organizations: number;
  apiCallsPerMonth: number;
  dataRetentionDays: number;
  storageGB: number;
}

export interface LicenseFeatures {
  // Core Features
  dashboard: boolean;
  deviceManagement: boolean;
  userManagement: boolean;
  basicSecurity: boolean;
  
  // UI Features
  darkTheme: boolean;
  customThemes: boolean;
  advancedCharts: boolean;
  realtimeUpdates: boolean;
  
  // Advanced Features
  multiOrganization: boolean;
  advancedPKI: boolean;
  vaultIntegration: boolean;
  hsmSupport: boolean;
  
  // Compliance
  etsiBasic: boolean; // Provisions 1-5
  etsiFull: boolean;  // All 13 provisions
  complianceReporting: boolean;
  auditLogs: boolean;
  
  // AI & Analytics
  aiAnalytics: boolean;
  ragSupport: boolean;
  predictiveMaintenance: boolean;
  anomalyDetection: boolean;
  
  // Digital Twin
  digitalTwin: boolean;
  deviceShadow: boolean;
  simulation: boolean;
  
  // Extended Connectivity
  industrialProtocols: boolean;
  opcua: boolean;
  modbus: boolean;
  lorawan: boolean;
  nbiot: boolean;
  
  // API Features
  graphqlAPI: boolean;
  websocketAPI: boolean;
  customDomains: boolean;
  edgeFunctions: boolean;
  
  // Enterprise
  sla: boolean;
  dedicatedSupport: boolean;
  customIntegrations: boolean;
  whiteLabel: boolean;
}

export interface License {
  id: string;
  edition: LicenseEdition;
  organizationId: string;
  organizationName: string;
  issuedAt: Date;
  expiresAt: Date;
  isActive: boolean;
  limits: LicenseLimits;
  features: LicenseFeatures;
  metadata?: {
    contactEmail?: string;
    supportTier?: string;
    customizations?: Record<string, any>;
  };
}

// Feature availability by edition
export const EDITION_FEATURES: Record<LicenseEdition, Partial<LicenseFeatures>> = {
  community: {
    // Core Features
    dashboard: true,
    deviceManagement: true,
    userManagement: true,
    basicSecurity: true,
    
    // UI Features
    darkTheme: false,
    customThemes: false,
    advancedCharts: false,
    realtimeUpdates: false,
    
    // Basic Compliance
    etsiBasic: true,
    etsiFull: false,
    complianceReporting: false,
    auditLogs: true,
    
    // All other features: false
  },
  
  startup: {
    // Everything from community plus:
    dashboard: true,
    deviceManagement: true,
    userManagement: true,
    basicSecurity: true,
    darkTheme: true,
    advancedCharts: true,
    realtimeUpdates: true,
    etsiBasic: true,
    auditLogs: true,
    graphqlAPI: true,
    websocketAPI: true,
    customDomains: true,
    
    // Still limited
    multiOrganization: false,
    advancedPKI: false,
    etsiFull: false,
    aiAnalytics: false,
    digitalTwin: false,
    industrialProtocols: false,
  },
  
  business: {
    // Most features enabled
    dashboard: true,
    deviceManagement: true,
    userManagement: true,
    basicSecurity: true,
    darkTheme: true,
    customThemes: true,
    advancedCharts: true,
    realtimeUpdates: true,
    multiOrganization: true,
    advancedPKI: true,
    vaultIntegration: true,
    etsiBasic: true,
    etsiFull: true,
    complianceReporting: true,
    auditLogs: true,
    graphqlAPI: true,
    websocketAPI: true,
    customDomains: true,
    edgeFunctions: true,
    sla: true,
    
    // Premium features still limited
    hsmSupport: false,
    aiAnalytics: false,
    digitalTwin: false,
    whiteLabel: false,
  },
  
  enterprise: {
    // All features enabled
    dashboard: true,
    deviceManagement: true,
    userManagement: true,
    basicSecurity: true,
    darkTheme: true,
    customThemes: true,
    advancedCharts: true,
    realtimeUpdates: true,
    multiOrganization: true,
    advancedPKI: true,
    vaultIntegration: true,
    hsmSupport: true,
    etsiBasic: true,
    etsiFull: true,
    complianceReporting: true,
    auditLogs: true,
    aiAnalytics: true,
    ragSupport: true,
    predictiveMaintenance: true,
    anomalyDetection: true,
    digitalTwin: true,
    deviceShadow: true,
    simulation: true,
    industrialProtocols: true,
    opcua: true,
    modbus: true,
    lorawan: true,
    nbiot: true,
    graphqlAPI: true,
    websocketAPI: true,
    customDomains: true,
    edgeFunctions: true,
    sla: true,
    dedicatedSupport: true,
    customIntegrations: true,
    whiteLabel: true,
  },
};

// Edition limits
export const EDITION_LIMITS: Record<LicenseEdition, LicenseLimits> = {
  community: {
    devices: 100,
    users: 10,
    organizations: 1,
    apiCallsPerMonth: 10000,
    dataRetentionDays: 30,
    storageGB: 1,
  },
  startup: {
    devices: 10000,
    users: 50,
    organizations: 1,
    apiCallsPerMonth: 1000000,
    dataRetentionDays: 30,
    storageGB: 100,
  },
  business: {
    devices: 100000,
    users: 500,
    organizations: 10,
    apiCallsPerMonth: 10000000,
    dataRetentionDays: 90,
    storageGB: 1000,
  },
  enterprise: {
    devices: -1, // Unlimited
    users: -1,   // Unlimited
    organizations: -1, // Unlimited
    apiCallsPerMonth: -1, // Unlimited
    dataRetentionDays: -1, // Unlimited
    storageGB: -1, // Unlimited
  },
};