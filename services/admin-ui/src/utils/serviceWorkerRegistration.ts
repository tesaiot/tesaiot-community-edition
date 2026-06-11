/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { showNotification } from '@/utils/notifications';

type Config = {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onError?: (error: Error) => void;
};

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
);

function registerValidSW(swUrl: string, config?: Config) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }
        
        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // New content is available; please refresh
              console.log('New content is available; please refresh.');
              
              showNotification({
                type: 'info',
                title: 'Update Available',
                message: 'New content is available. Click to refresh.',
                duration: 0,
                action: {
                  label: 'Refresh',
                  onClick: () => {
                    // Tell SW to skip waiting
                    if (registration.waiting) {
                      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                    }
                    window.location.reload();
                  }
                }
              });

              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
            } else {
              // Content is cached for offline use
              console.log('Content is cached for offline use.');

              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        };
      };
    })
    .catch((error) => {
      console.error('Error during service worker registration:', error);
      if (config && config.onError) {
        config.onError(error);
      }
    });
}

function checkValidServiceWorker(swUrl: string, config?: Config) {
  // Check if the service worker can be found
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      // Ensure service worker exists, and that we really are getting a JS file
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // No service worker found. Probably a different app. Reload the page
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Service worker found. Proceed as normal
        registerValidSW(swUrl, config);
      }
    })
    .catch(() => {
      console.log('No internet connection found. App is running in offline mode.');
    });
}

export function register(config?: Config) {
  if ('serviceWorker' in navigator) {
    // Wait for the page to load
    window.addEventListener('load', () => {
      const swUrl = `${import.meta.env.BASE_URL}service-worker.js`;

      if (isLocalhost) {
        // This is running on localhost. Check if a service worker still exists or not
        checkValidServiceWorker(swUrl, config);

        // Add some additional logging to localhost
        navigator.serviceWorker.ready.then(() => {
          console.log(
            'This web app is being served cache-first by a service ' +
              'worker. To learn more, visit https://cra.link/PWA'
          );
        });
      } else {
        // Is not localhost. Just register service worker
        registerValidSW(swUrl, config);
      }
    });
  }
}

/**
 * Enhanced unregister function with complete cleanup
 */
export async function unregister(): Promise<boolean> {
  if ('serviceWorker' in navigator) {
    try {
      const result = await permanentCleanup();
      return result.success;
    } catch (error) {
      console.error('Unregister error:', error);
      return false;
    }
  }
  return true; // No service workers supported, so "success"
}

/**
 * Advanced service worker cleanup mechanism
 * Permanently unregisters all service workers and clears all caches
 */
export async function permanentCleanup(): Promise<{
  success: boolean;
  details: {
    serviceWorkersUnregistered: number;
    cachesCleared: number;
    storageCleared: boolean;
  }
  errors: string[];
}> {
  const result = {
    success: true,
    details: {
      serviceWorkersUnregistered: 0,
      cachesCleared: 0,
      storageCleared: false
    },
    errors: [] as string[]
  };

  try {
    // 1. Unregister ALL service workers
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      
      for (const registration of registrations) {
        try {
          const success = await registration.unregister();
          if (success) {
            result.details.serviceWorkersUnregistered++;
            console.log('Unregistered SW:', registration.scope);
          }
        } catch (error) {
          result.errors.push(`Failed to unregister SW ${registration.scope}: ${error}`);
          result.success = false;
        }
      }
    }

    // 2. Clear ALL caches
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      
      for (const cacheName of cacheNames) {
        try {
          const success = await caches.delete(cacheName);
          if (success) {
            result.details.cachesCleared++;
            console.log('Deleted cache:', cacheName);
          }
        } catch (error) {
          result.errors.push(`Failed to delete cache ${cacheName}: ${error}`);
          result.success = false;
        }
      }
    }

    // 3. Clear browser storage
    try {
      localStorage.clear();
      sessionStorage.clear();
      
      // Clear IndexedDB if present
      if ('indexedDB' in window) {
        // Note: This is a basic cleanup - specific DB names would need to be known for complete cleanup
        const databases = await indexedDB.databases?.() || [];
        for (const db of databases) {
          if (db.name) {
            indexedDB.deleteDatabase(db.name);
          }
        }
      }
      
      result.details.storageCleared = true;
    } catch (error) {
      result.errors.push(`Failed to clear storage: ${error}`);
      result.success = false;
    }

  } catch (error) {
    result.errors.push(`General cleanup error: ${error}`);
    result.success = false;
  }

  return result;
}

/**
 * Legacy cache clearing function - maintained for compatibility
 */
export async function clearCaches() {
  const result = await permanentCleanup();
  
  if (!result.success) {
    console.warn('Cache clearing had some issues:', result.errors);
  }
  
  return result;
}

/**
 * Automatic startup cleanup - runs on app initialization
 * Removes old/stale service workers and caches
 */
export async function startupCleanup(): Promise<void> {
  try {
    // Check if there are any service workers that need cleanup
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      
      // If we find any registrations and SW is supposed to be disabled, clean them up
      if (registrations.length > 0) {
        console.log(`Found ${registrations.length} service worker(s) that need cleanup`);
        
        const result = await permanentCleanup();
        
        if (result.success) {
          console.log('🧹 Startup cleanup completed:', result.details);
        } else {
          console.warn('⚠️ Startup cleanup had issues:', result.errors);
        }
      }
    }
    
    // Also clean up old caches that might be lingering
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      const oldCachePattern = /tesa-admin-ui-(v[0-9]|dynamic-v[0-9])/;
      
      for (const cacheName of cacheNames) {
        if (oldCachePattern.test(cacheName)) {
          try {
            await caches.delete(cacheName);
            console.log('🧹 Cleaned old cache:', cacheName);
          } catch (error) {
            console.warn('Failed to clean old cache:', cacheName, error);
          }
        }
      }
    }
    
  } catch (error) {
    console.warn('Startup cleanup failed:', error);
  }
}

/**
 * Check if service workers are causing issues
 * Returns diagnostic information about current SW state
 */
export async function diagnoseTserviceWorkerIssues(): Promise<{
  hasServiceWorkers: boolean;
  registrations: ServiceWorkerRegistration[];
  caches: string[];
  recommendCleanup: boolean;
}> {
  const diagnosis = {
    hasServiceWorkers: false,
    registrations: [] as ServiceWorkerRegistration[],
    caches: [] as string[],
    recommendCleanup: false
  };
  
  try {
    // Check service workers
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      diagnosis.registrations = registrations;
      diagnosis.hasServiceWorkers = registrations.length > 0;
    }
    
    // Check caches
    if ('caches' in window) {
      diagnosis.caches = await caches.keys();
    }
    
    // Recommend cleanup if we have SW or old caches when SW should be disabled
    diagnosis.recommendCleanup = diagnosis.hasServiceWorkers || 
      diagnosis.caches.some(name => name.includes('tesa-admin-ui'));
    
  } catch (error) {
    console.warn('Service worker diagnosis failed:', error);
  }
  
  return diagnosis;
}