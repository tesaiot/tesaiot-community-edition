/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect } from 'react';
import { License } from '@/services/license/types';

const STABLE_LICENSE: License = {
  id: 'license-community-001',
  edition: 'community',
  type: 'community',
  isActive: true,
  organizationId: 'default-org',
  organizationName: 'Default Organization',
  issuedAt: new Date(),
  expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year
  features: {
    // Community Edition capability set (single-organization, self-host).
    darkTheme: true,
    customThemes: false,
    advancedCharts: false,
    realtimeUpdates: true,
    multiOrganization: false,   // hides the platform-admin "Organization" menu
    advancedPKI: true,          // Vault PKI cert lifecycle is a core CE capability
    vaultIntegration: true,
    hsmSupport: false,
    etsiBasic: true,
    etsiFull: false,
    complianceReporting: false,
    auditLogs: true,
    aiAnalytics: false,
    ragSupport: false,
    predictiveMaintenance: false,
    anomalyDetection: false,
    digitalTwin: false,
    deviceShadow: false,
    simulation: false,
    industrialProtocols: false,
    restAPI: true,
    graphqlAPI: false,
    websocketAPI: true,
    webhooks: false,
    unlimitedDevices: true,
    dedicatedPKI: false,
    customBranding: false,
    prioritySupport: false,
    ssoIntegration: false,
    bulkOperations: false,
    advancedSecurity: true,
    customReports: false,
    auditLogging: true,
    realtimeWebsocket: true,
    multiTenancy: false
  },
  limits: {
    devices: -1,
    users: -1,
    organizations: 1,           // single-organization edition
    apiCallsPerMonth: -1,
    dataRetentionDays: -1,
    storageGB: -1
  }
};

export function useLicenseStable() {
  const [license] = useState<License>(STABLE_LICENSE);
  const [isLoading] = useState(false);

  // Helper functions
  const hasFeature = (feature: keyof License['features']): boolean => {
    return license.features[feature] === true;
  };

  const hasFeatures = (...features: (keyof License['features'])[]): boolean => {
    return features.every(feature => hasFeature(feature));
  };

  const hasAnyFeature = (...features: (keyof License['features'])[]): boolean => {
    return features.some(feature => hasFeature(feature));
  };

  const canAddDevice = (currentCount: number): boolean => {
    return license.limits.devices === -1 || currentCount < license.limits.devices;
  };

  const canAddUser = (currentCount: number): boolean => {
    return license.limits.users === -1 || currentCount < license.limits.users;
  };

  const canAddOrganization = (currentCount: number): boolean => {
    return license.limits.organizations === -1 || currentCount < license.limits.organizations;
  };

  const isCommercial = (): boolean => {
    return license.edition !== 'community';
  };

  const getAvailableThemes = (): string[] => {
    if (hasFeature('customThemes')) {
      return ['light', 'dark', 'blue', 'green', 'purple'];
    }
    if (hasFeature('darkTheme')) {
      return ['light', 'dark'];
    }
    return ['light'];
  };

  const formatLimit = (value: number, singular: string, plural?: string): string => {
    if (value === -1) return 'Unlimited';
    const p = plural || `${singular}s`;
    return value === 1 ? `1 ${singular}` : `${value} ${p}`;
  };

  const getUpgradeUrl = (): string => {
    return '/pricing';
  };

  return {
    license,
    isLoading,
    edition: license.edition,
    isActive: license.isActive,
    limits: license.limits,
    features: license.features,
    
    // Feature checks
    hasFeature,
    hasFeatures,
    hasAnyFeature,
    
    // Limit checks
    canAddDevice,
    canAddUser,
    canAddOrganization,
    
    // Helpers
    isCommercial,
    getAvailableThemes,
    formatLimit,
    getUpgradeUrl,
  };
}