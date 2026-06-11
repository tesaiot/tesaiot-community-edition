/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect } from 'react';
import { TesaRouting } from '@/routing/TesaRouting';
// import { HelmetProvider } from 'react-helmet-async'; // Removed - not compatible with React 19
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LoadingBarContainer } from 'react-top-loading-bar';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from './auth/providers/tesa-provider';
import { I18nProvider } from './providers/i18n-provider';
import { LicenseProvider } from './providers/license-provider';
import { UICustomizationProvider } from './providers/ui-customization-provider';
import { ModulesProvider } from './providers/modules-provider';
import { QueryProvider } from './providers/query-provider';
import { SettingsProvider } from './providers/settings-provider';
import { EnhancedThemeProvider } from './providers/enhanced-theme-provider';
import { TooltipsProvider } from './providers/tooltips-provider';
import { NotificationProvider } from '@/features/notifications/NotificationService';
import { initializeVersionChecker } from '@/utils/versionChecker';
import * as serviceWorkerRegistration from '@/utils/serviceWorkerRegistration';
import { initializeServiceWorkerCleanup, setupEmergencyCleanup } from '@/utils/serviceWorkerCleanup';

const { BASE_URL } = import.meta.env;

export function App() {
  const queryClient = new QueryClient();
  
  useEffect(() => {
    // Initialize service worker cleanup mechanism on app startup
    const initializeApp = async () => {
      try {
        // PERMANENT SOLUTION: Initialize automatic service worker cleanup
        // This ensures old service workers are removed and caches are cleared
        console.log('🚀 Initializing permanent service worker cleanup mechanism...');
        await initializeServiceWorkerCleanup();
        
        // Setup emergency cleanup function available in console
        setupEmergencyCleanup();
        
        console.log('✅ Service worker cleanup mechanism initialized successfully');
      } catch (error) {
        console.error('❌ Failed to initialize service worker cleanup:', error);
      }
    };
    
    // Run initialization
    initializeApp();
    
    // Version checker temporarily disabled due to false update notifications
    // TODO: Fix version.json serving before re-enabling
    /*
    initializeVersionChecker({
      checkInterval: 5 * 60 * 1000, // 5 minutes
      autoReload: false, // Disabled to prevent automatic page refreshes
      notifyUser: true,
      reloadDelay: 5000 // 5 seconds
    });
    */
    
    // Register service worker - PERMANENTLY DISABLED in favor of cleanup mechanism
    // The cleanup mechanism above ensures any existing service workers are removed
    /*
    serviceWorkerRegistration.register({
      onSuccess: (registration) => {
        console.log('Service Worker registered successfully:', registration);
      },
      onUpdate: (registration) => {
        console.log('Service Worker update available:', registration);
      },
      onError: (error) => {
        console.error('Service Worker registration failed:', error);
      }
    });
    */
    
    // Log build info
    if (typeof __BUILD_TIME__ !== 'undefined') {
      console.log('App Build Info:', {
        version: __APP_VERSION__,
        buildTime: __BUILD_TIME__,
        gitCommit: __GIT_COMMIT__
      });
    }
    
    return () => {
      // Cleanup on unmount if needed
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LicenseProvider>
          <UICustomizationProvider>
            <SettingsProvider>
              <EnhancedThemeProvider>
                <I18nProvider>
                  <TooltipsProvider>
                    <NotificationProvider>
                      <QueryProvider>
                        <LoadingBarContainer>
                          <BrowserRouter basename={BASE_URL}>
                              <Toaster />
                              <ModulesProvider>
                                <TesaRouting />
                              </ModulesProvider>
                            </BrowserRouter>
                          </LoadingBarContainer>
                        </QueryProvider>
                      </NotificationProvider>
                    </TooltipsProvider>
                </I18nProvider>
              </EnhancedThemeProvider>
            </SettingsProvider>
          </UICustomizationProvider>
        </LicenseProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
