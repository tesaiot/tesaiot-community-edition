/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useLicenseContext } from './license-provider';
import { tesaApi } from '@/services/api/tesaApi';

interface UIElementVisibility {
  visible: boolean;
  enabled: boolean;
  configuration?: Record<string, any>;
  reason?: string;
  tier_restricted?: boolean;
  override_applied?: boolean;
}

interface UICustomizationContextType {
  uiElements: Record<string, UIElementVisibility>;
  organizationTier: string;
  isLoading: boolean;
  error: string | null;
  checkUIElement: (elementKey: string) => boolean;
  isUIElementVisible: (elementKey: string) => boolean;
  isUIElementEnabled: (elementKey: string) => boolean;
  getUIElementConfig: (elementKey: string) => Record<string, any> | undefined;
  hasAnyUIElement: (elementKeys: string[]) => boolean;
  hasAllUIElements: (elementKeys: string[]) => boolean;
  refreshUIConfiguration: () => Promise<void>;
}

const UICustomizationContext = createContext<UICustomizationContextType | undefined>(undefined);

export function UICustomizationProvider({ children }: { children: ReactNode }) {
  const [uiElements, setUIElements] = useState<Record<string, UIElementVisibility>>({});
  const [organizationTier, setOrganizationTier] = useState<string>('STARTUP');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { user } = useAuth();
  const { hasFeature } = useLicenseContext();

  // Fetch UI configuration from backend
  const fetchUIConfiguration = useCallback(async () => {
    console.log('UICustomizationProvider: user object:', {
      email: user?.email,
      role: user?.role,
      organization_id: user?.organization_id,
      full_user: user
    });
    
    if (!user?.organization_id) {
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      console.log('UICustomizationProvider: Fetching UI config for org:', user.organization_id);
      const response = await tesaApi.get(`/api/v1/ui-customization/organizations/${user.organization_id}/ui-configuration`);
      
      if (response.data) {
        setUIElements(response.data.ui_elements || {});
        setOrganizationTier(response.data.tier || 'STARTUP');
      }
    } catch (err: any) {
      console.error('Failed to fetch UI customization configuration:', err);
      setError(err.message || 'Failed to load UI configuration');
      
      // Fallback to defaults on error
      setUIElements({});
      setOrganizationTier('STARTUP');
    } finally {
      setIsLoading(false);
    }
  }, [user?.organization_id]);

  // Fetch configuration on mount and when organization changes
  useEffect(() => {
    fetchUIConfiguration();
  }, [fetchUIConfiguration]);

  // Check if a UI element should be displayed
  const checkUIElement = useCallback((elementKey: string): boolean => {
    const element = uiElements[elementKey];
    if (!element) return false;
    
    // Check both visibility and enabled status
    return element.visible && element.enabled;
  }, [uiElements]);

  // Check if UI element is visible (might be disabled)
  const isUIElementVisible = useCallback((elementKey: string): boolean => {
    const element = uiElements[elementKey];
    return element?.visible || false;
  }, [uiElements]);

  // Check if UI element is enabled (might not be visible)
  const isUIElementEnabled = useCallback((elementKey: string): boolean => {
    const element = uiElements[elementKey];
    return element?.enabled || false;
  }, [uiElements]);

  // Get UI element configuration
  const getUIElementConfig = useCallback((elementKey: string): Record<string, any> | undefined => {
    const element = uiElements[elementKey];
    return element?.configuration;
  }, [uiElements]);

  // Check if any of the UI elements are available
  const hasAnyUIElement = useCallback((elementKeys: string[]): boolean => {
    return elementKeys.some(key => checkUIElement(key));
  }, [checkUIElement]);

  // Check if all UI elements are available
  const hasAllUIElements = useCallback((elementKeys: string[]): boolean => {
    return elementKeys.every(key => checkUIElement(key));
  }, [checkUIElement]);

  // Refresh UI configuration
  const refreshUIConfiguration = useCallback(async () => {
    await fetchUIConfiguration();
  }, [fetchUIConfiguration]);

  const value: UICustomizationContextType = {
    uiElements,
    organizationTier,
    isLoading,
    error,
    checkUIElement,
    isUIElementVisible,
    isUIElementEnabled,
    getUIElementConfig,
    hasAnyUIElement,
    hasAllUIElements,
    refreshUIConfiguration
  };

  return (
    <UICustomizationContext.Provider value={value}>
      {children}
    </UICustomizationContext.Provider>
  );
}

export function useUICustomization() {
  const context = useContext(UICustomizationContext);
  if (context === undefined) {
    // Return safe defaults to prevent crashes
    console.warn('useUICustomization called outside UICustomizationProvider - using defaults');
    return {
      uiElements: {},
      organizationTier: 'STARTUP',
      isLoading: false,
      error: null,
      checkUIElement: () => false,
      isUIElementVisible: () => false,
      isUIElementEnabled: () => false,
      getUIElementConfig: () => undefined,
      hasAnyUIElement: () => false,
      hasAllUIElements: () => false,
      refreshUIConfiguration: async () => {}
    };
  }
  return context;
}

// Component for conditional rendering based on UI customization
export function UIElementGate({ 
  element, 
  children, 
  fallback = null,
  requireAll = false
}: { 
  element: string | string[];
  children: ReactNode;
  fallback?: ReactNode;
  requireAll?: boolean;
}) {
  const { checkUIElement, hasAnyUIElement, hasAllUIElements } = useUICustomization();
  
  const hasAccess = Array.isArray(element) 
    ? (requireAll ? hasAllUIElements(element) : hasAnyUIElement(element))
    : checkUIElement(element);
  
  if (!hasAccess) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}

// HOC for UI element gated components
export function withUIElement<P extends object>(
  Component: React.ComponentType<P>,
  elementKey: string,
  fallback?: React.ComponentType<P>
) {
  return function UIElementGatedComponent(props: P) {
    const { checkUIElement } = useUICustomization();
    
    if (checkUIElement(elementKey)) {
      return <Component {...props} />;
    }
    
    if (fallback) {
      const FallbackComponent = fallback;
      return <FallbackComponent {...props} />;
    }
    
    return null;
  };
}

// Upgrade prompt component for restricted UI elements
export function UIElementUpgradePrompt({ 
  element,
  tier,
  message 
}: { 
  element: string;
  tier?: string;
  message?: string;
}) {
  const { organizationTier } = useUICustomization();
  
  return (
    <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <span>
          {message || `This feature requires ${tier || 'a higher'} tier. Current tier: ${organizationTier}`}
        </span>
      </div>
    </div>
  );
}