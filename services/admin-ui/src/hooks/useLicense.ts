/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useState } from 'react';
import { licenseService } from '@/services/license/LicenseService';
import { License, LicenseFeatures, LicenseLimits } from '@/services/license/types';

// TEMPORARY: Import stable license to fix swapping issue
import { useLicenseStable } from './useLicenseStable';

export function useLicense() {
  // TEMPORARY: Return stable enterprise license to prevent swapping
  return useLicenseStable();
}

// Original implementation (temporarily disabled to fix swapping)
export function useLicenseOriginal() {
  const [license, setLicense] = useState<License | null>(licenseService.getLicense());
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Initial load
    const currentLicense = licenseService.getLicense();
    setLicense(currentLicense);

    // Set up periodic check
    const interval = setInterval(() => {
      const updatedLicense = licenseService.getLicense();
      setLicense(prevLicense => {
        // Only update if the license has actually changed
        if (JSON.stringify(updatedLicense) !== JSON.stringify(prevLicense)) {
          return updatedLicense;
        }
        return prevLicense;
      });
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Feature checks
  const hasFeature = (feature: keyof LicenseFeatures): boolean => {
    return licenseService.hasFeature(feature);
  };

  const hasFeatures = (...features: (keyof LicenseFeatures)[]): boolean => {
    return licenseService.hasFeatures(...features);
  };

  const hasAnyFeature = (...features: (keyof LicenseFeatures)[]): boolean => {
    return licenseService.hasAnyFeature(...features);
  };

  // Limit checks
  const canAddDevice = (currentCount: number): boolean => {
    return licenseService.canAddDevice(currentCount);
  };

  const canAddUser = (currentCount: number): boolean => {
    return licenseService.canAddUser(currentCount);
  };

  const canAddOrganization = (currentCount: number): boolean => {
    return licenseService.canAddOrganization(currentCount);
  };

  // Helper functions
  const isCommercial = (): boolean => {
    return licenseService.isCommercial();
  };

  const getAvailableThemes = (): string[] => {
    return licenseService.getAvailableThemes();
  };

  const formatLimit = (value: number, singular: string, plural?: string): string => {
    return licenseService.formatLimit(value, singular, plural);
  };

  return {
    license,
    isLoading,
    edition: license?.edition || 'community',
    isActive: licenseService.isLicenseActive(),
    limits: license?.limits || {} as LicenseLimits,
    features: license?.features || {} as LicenseFeatures,
    
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
    getUpgradeUrl: () => licenseService.getUpgradeUrl(),
  };
}

// Specific feature hooks for common use cases
export function useThemeAccess() {
  const { hasFeature, getAvailableThemes } = useLicense();
  
  return {
    canUseDarkTheme: hasFeature('darkTheme'),
    canUseCustomThemes: hasFeature('customThemes'),
    availableThemes: getAvailableThemes(),
  };
}

export function useOrganizationAccess() {
  const { hasFeature, canAddOrganization } = useLicense();
  
  return {
    hasMultiOrg: hasFeature('multiOrganization'),
    canAddOrganization,
  };
}

export function useAdvancedFeatures() {
  const { hasFeature } = useLicense();
  
  return {
    hasAI: hasFeature('aiAnalytics'),
    hasDigitalTwin: hasFeature('digitalTwin'),
    hasIndustrialProtocols: hasFeature('industrialProtocols'),
    hasAdvancedPKI: hasFeature('advancedPKI'),
    hasFullCompliance: hasFeature('etsiFull'),
  };
}