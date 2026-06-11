/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useLicense } from '@/hooks/useLicense';
import { License, LicenseFeatures, LicenseLimits } from '@/services/license/types';

interface LicenseContextType {
  license: License | null;
  edition: string;
  isActive: boolean;
  limits: LicenseLimits;
  features: LicenseFeatures;
  hasFeature: (feature: keyof LicenseFeatures) => boolean;
  hasFeatures: (...features: (keyof LicenseFeatures)[]) => boolean;
  hasAnyFeature: (...features: (keyof LicenseFeatures)[]) => boolean;
  canAddDevice: (currentCount: number) => boolean;
  canAddUser: (currentCount: number) => boolean;
  canAddOrganization: (currentCount: number) => boolean;
  isCommercial: () => boolean;
  getAvailableThemes: () => string[];
  formatLimit: (value: number, singular: string, plural?: string) => string;
  getUpgradeUrl: () => string;
}

const LicenseContext = createContext<LicenseContextType | undefined>(undefined);

export function LicenseProvider({ children }: { children: ReactNode }) {
  const licenseData = useLicense();

  return (
    <LicenseContext.Provider value={licenseData}>
      {children}
    </LicenseContext.Provider>
  );
}

export function useLicenseContext() {
  const context = useContext(LicenseContext);
  if (context === undefined) {
    // PRODUCTION FIX: Return safe defaults instead of crashing
    console.warn('useLicenseContext called outside LicenseProvider - using defaults');
    return {
      isLoading: false,
      licenseInfo: null,
      hasFeature: () => false,
      isCommercialEdition: false,
      isProfessionalEdition: false,
      refreshLicense: async () => {},
    };
  }
  return context;
}

// HOC for feature-gated components
export function withFeature<P extends object>(
  Component: React.ComponentType<P>,
  feature: keyof LicenseFeatures,
  fallback?: React.ComponentType<P>
) {
  return function FeatureGatedComponent(props: P) {
    const { hasFeature } = useLicenseContext();
    
    if (hasFeature(feature)) {
      return <Component {...props} />;
    }
    
    if (fallback) {
      const FallbackComponent = fallback;
      return <FallbackComponent {...props} />;
    }
    
    return null;
  };
}

// Component for conditional rendering based on features
export function RequireFeature({ 
  feature, 
  children, 
  fallback = null 
}: { 
  feature: keyof LicenseFeatures | (keyof LicenseFeatures)[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasFeature, hasFeatures } = useLicenseContext();
  
  const hasRequiredFeatures = Array.isArray(feature) 
    ? hasFeatures(...feature)
    : hasFeature(feature);
  
  return hasRequiredFeatures ? <>{children}</> : <>{fallback}</>;
}

// Component for showing upgrade prompts
export function UpgradePrompt({ 
  feature,
  message,
  className = ''
}: {
  feature: keyof LicenseFeatures;
  message?: string;
  className?: string;
}) {
  const { hasFeature, edition, getUpgradeUrl } = useLicenseContext();
  
  if (hasFeature(feature)) {
    return null;
  }
  
  const defaultMessage = `This feature requires an upgraded license. You are currently on the ${edition} edition.`;
  
  return (
    <div className={`bg-yellow-50 border border-yellow-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12zm0-9a1 1 0 011 1v4a1 1 0 11-2 0V8a1 1 0 011-1zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm text-yellow-700">
            {message || defaultMessage}
          </p>
          <p className="mt-2">
            <a
              href={getUpgradeUrl()}
              className="text-sm font-medium text-yellow-700 hover:text-yellow-600"
            >
              Upgrade now →
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}