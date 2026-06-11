/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

interface CleanupResult {
  success: boolean;
  serviceWorkersRemoved: number;
  cachesCleared: number;
  storageCleared: boolean;
  errors: string[];
  timestamp: number;
}

interface ServiceWorkerState {
  registrations: ServiceWorkerRegistration[];
  caches: string[];
  hasActiveWorkers: boolean;
  needsCleanup: boolean;
}

class ServiceWorkerCleanupManager {
  private static instance: ServiceWorkerCleanupManager;
  private cleanupInterval: number | null = null;
  private isCleanupInProgress = false;
  
  public static getInstance(): ServiceWorkerCleanupManager {
    if (!ServiceWorkerCleanupManager.instance) {
      ServiceWorkerCleanupManager.instance = new ServiceWorkerCleanupManager();
    }
    return ServiceWorkerCleanupManager.instance;
  }

  /**
   * Initialize the cleanup manager with automatic monitoring
   */
  public async initialize(): Promise<void> {
    console.log('🚀 Initializing Service Worker Cleanup Manager');
    
    // Perform initial cleanup
    await this.performStartupCleanup();
    
    // Set up periodic monitoring (every 5 minutes)
    this.startPeriodicCleanup();
    
    // Listen for page visibility changes to trigger cleanup
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        this.checkAndCleanupIfNeeded();
      }
    });
    
    // Listen for beforeunload to ensure cleanup on page exit
    window.addEventListener('beforeunload', () => {
      this.performQuickCleanup();
    });
  }

  /**
   * Perform comprehensive startup cleanup
   */
  private async performStartupCleanup(): Promise<void> {
    try {
      const state = await this.assessServiceWorkerState();
      
      if (state.needsCleanup) {
        console.log('🧹 Performing startup service worker cleanup...');
        const result = await this.performCompleteCleanup();
        
        if (result.success) {
          console.log('✅ Startup cleanup completed successfully:', {
            serviceWorkersRemoved: result.serviceWorkersRemoved,
            cachesCleared: result.cachesCleared
          });
        } else {
          console.warn('⚠️ Startup cleanup had issues:', result.errors);
        }
      }
    } catch (error) {
      console.error('❌ Startup cleanup failed:', error);
    }
  }

  /**
   * Assess current service worker state
   */
  private async assessServiceWorkerState(): Promise<ServiceWorkerState> {
    const state: ServiceWorkerState = {
      registrations: [],
      caches: [],
      hasActiveWorkers: false,
      needsCleanup: false
    };

    try {
      // Check service worker registrations
      if ('serviceWorker' in navigator) {
        state.registrations = await navigator.serviceWorker.getRegistrations();
        state.hasActiveWorkers = state.registrations.length > 0;
      }

      // Check caches
      if ('caches' in window) {
        state.caches = await caches.keys();
      }

      // Determine if cleanup is needed
      state.needsCleanup = state.hasActiveWorkers || 
        state.caches.some(name => this.isOldTesaCache(name));

    } catch (error) {
      console.warn('Failed to assess service worker state:', error);
    }

    return state;
  }

  /**
   * Check if a cache name is an old TESA cache that should be cleaned
   */
  private isOldTesaCache(cacheName: string): boolean {
    const tesaCachePatterns = [
      /^tesa-admin-ui-v\d+$/,
      /^tesa-admin-ui-dynamic-v\d+$/,
      /^tesa-/,
      /^workbox-/,
      /^sw-/
    ];
    
    return tesaCachePatterns.some(pattern => pattern.test(cacheName));
  }

  /**
   * Perform complete cleanup of service workers and caches
   */
  public async performCompleteCleanup(): Promise<CleanupResult> {
    if (this.isCleanupInProgress) {
      console.log('Cleanup already in progress, skipping...');
      return {
        success: false,
        serviceWorkersRemoved: 0,
        cachesCleared: 0,
        storageCleared: false,
        errors: ['Cleanup already in progress'],
        timestamp: Date.now()
      };
    }

    this.isCleanupInProgress = true;
    
    const result: CleanupResult = {
      success: true,
      serviceWorkersRemoved: 0,
      cachesCleared: 0,
      storageCleared: false,
      errors: [],
      timestamp: Date.now()
    };

    try {
      // 1. Unregister all service workers
      await this.unregisterAllServiceWorkers(result);
      
      // 2. Clear all caches
      await this.clearAllCaches(result);
      
      // 3. Clear storage
      await this.clearBrowserStorage(result);
      
      // 4. Force garbage collection if available
      this.forceGarbageCollection();

    } catch (error) {
      result.success = false;
      result.errors.push(`Complete cleanup failed: ${error}`);
    } finally {
      this.isCleanupInProgress = false;
    }

    return result;
  }

  /**
   * Unregister all service worker registrations
   */
  private async unregisterAllServiceWorkers(result: CleanupResult): Promise<void> {
    if (!('serviceWorker' in navigator)) {
      return;
    }

    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      
      for (const registration of registrations) {
        try {
          // Stop the service worker if it's active
          if (registration.active) {
            registration.active.postMessage({ type: 'SKIP_WAITING' });
          }
          
          const unregistered = await registration.unregister();
          if (unregistered) {
            result.serviceWorkersRemoved++;
            console.log('🗑️ Unregistered service worker:', registration.scope);
          }
        } catch (error) {
          result.errors.push(`Failed to unregister SW ${registration.scope}: ${error}`);
          result.success = false;
        }
      }
    } catch (error) {
      result.errors.push(`Failed to get service worker registrations: ${error}`);
      result.success = false;
    }
  }

  /**
   * Clear all browser caches
   */
  private async clearAllCaches(result: CleanupResult): Promise<void> {
    if (!('caches' in window)) {
      return;
    }

    try {
      const cacheNames = await caches.keys();
      
      for (const cacheName of cacheNames) {
        try {
          const deleted = await caches.delete(cacheName);
          if (deleted) {
            result.cachesCleared++;
            console.log('🗑️ Deleted cache:', cacheName);
          }
        } catch (error) {
          result.errors.push(`Failed to delete cache ${cacheName}: ${error}`);
          result.success = false;
        }
      }
    } catch (error) {
      result.errors.push(`Failed to get cache names: ${error}`);
      result.success = false;
    }
  }

  /**
   * Clear browser storage
   */
  private async clearBrowserStorage(result: CleanupResult): Promise<void> {
    try {
      // Clear localStorage (but preserve user preferences)
      const preserveKeys = ['theme', 'language', 'user-preferences'];
      const localStorageBackup: Record<string, string> = {};
      
      // Backup important keys
      preserveKeys.forEach(key => {
        const value = localStorage.getItem(key);
        if (value) {
          localStorageBackup[key] = value;
        }
      });
      
      // Clear all storage
      localStorage.clear();
      sessionStorage.clear();
      
      // Restore important keys
      Object.entries(localStorageBackup).forEach(([key, value]) => {
        localStorage.setItem(key, value);
      });

      // Clear IndexedDB
      if ('indexedDB' in window && indexedDB.databases) {
        const databases = await indexedDB.databases();
        for (const db of databases) {
          if (db.name && db.name.includes('tesa')) {
            try {
              indexedDB.deleteDatabase(db.name);
              console.log('🗑️ Deleted IndexedDB:', db.name);
            } catch (error) {
              result.errors.push(`Failed to delete IndexedDB ${db.name}: ${error}`);
            }
          }
        }
      }

      result.storageCleared = true;
    } catch (error) {
      result.errors.push(`Failed to clear browser storage: ${error}`);
      result.success = false;
    }
  }

  /**
   * Force garbage collection if available
   */
  private forceGarbageCollection(): void {
    try {
      // @ts-ignore - gc might be available in dev tools
      if (window.gc) {
        window.gc();
        console.log('🗑️ Forced garbage collection');
      }
    } catch (error) {
      // Ignore - gc is not always available
    }
  }

  /**
   * Perform quick cleanup (for page unload)
   */
  private performQuickCleanup(): void {
    try {
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(registrations => {
          registrations.forEach(registration => {
            registration.unregister().catch(() => {
              // Ignore errors during quick cleanup
            });
          });
        });
      }
    } catch (error) {
      // Ignore errors during quick cleanup
    }
  }

  /**
   * Start periodic cleanup monitoring
   */
  private startPeriodicCleanup(): void {
    // Check every 5 minutes
    this.cleanupInterval = window.setInterval(() => {
      this.checkAndCleanupIfNeeded();
    }, 5 * 60 * 1000);
  }

  /**
   * Check if cleanup is needed and perform if necessary
   */
  private async checkAndCleanupIfNeeded(): Promise<void> {
    try {
      const state = await this.assessServiceWorkerState();
      
      if (state.needsCleanup && !this.isCleanupInProgress) {
        console.log('🔍 Detected service workers that need cleanup');
        await this.performCompleteCleanup();
      }
    } catch (error) {
      console.warn('Periodic cleanup check failed:', error);
    }
  }

  /**
   * Stop periodic cleanup monitoring
   */
  public stopPeriodicCleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  /**
   * Get current cleanup manager status
   */
  public async getStatus(): Promise<{
    isActive: boolean;
    isCleanupInProgress: boolean;
    currentState: ServiceWorkerState;
  }> {
    return {
      isActive: this.cleanupInterval !== null,
      isCleanupInProgress: this.isCleanupInProgress,
      currentState: await this.assessServiceWorkerState()
    };
  }
}

// Export singleton instance and utility functions
export const serviceWorkerCleanupManager = ServiceWorkerCleanupManager.getInstance();

/**
 * Initialize service worker cleanup on app startup
 */
export async function initializeServiceWorkerCleanup(): Promise<void> {
  await serviceWorkerCleanupManager.initialize();
}

/**
 * Manually trigger complete service worker cleanup
 */
export async function triggerServiceWorkerCleanup(): Promise<CleanupResult> {
  return await serviceWorkerCleanupManager.performCompleteCleanup();
}

/**
 * Get service worker cleanup status
 */
export async function getServiceWorkerCleanupStatus() {
  return await serviceWorkerCleanupManager.getStatus();
}

/**
 * Emergency cleanup function - can be called from console
 * Usage: window.emergencyServiceWorkerCleanup()
 */
export function setupEmergencyCleanup(): void {
  (window as any).emergencyServiceWorkerCleanup = async () => {
    console.log('🚨 Emergency service worker cleanup initiated...');
    const result = await triggerServiceWorkerCleanup();
    console.log('🚨 Emergency cleanup result:', result);
    
    if (result.success) {
      console.log('✅ Emergency cleanup successful - page will reload in 3 seconds');
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } else {
      console.log('❌ Emergency cleanup had issues:', result.errors);
      console.log('Manual steps may be required');
    }
    
    return result;
  };
  
  console.log('🚨 Emergency cleanup function available: window.emergencyServiceWorkerCleanup()');
}

export default serviceWorkerCleanupManager;