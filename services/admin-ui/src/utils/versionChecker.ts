/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { showNotification } from '@/utils/notifications';

interface VersionInfo {
  version: string;
  buildId: string;
  buildTime: string;
  integrity: string;
}

interface VersionCheckOptions {
  checkInterval?: number; // milliseconds
  autoReload?: boolean;
  notifyUser?: boolean;
  reloadDelay?: number; // milliseconds
}

class VersionChecker {
  private currentVersion: VersionInfo | null = null;
  private checkTimer: NodeJS.Timeout | null = null;
  private isChecking = false;
  private reloadScheduled = false;
  private options: Required<VersionCheckOptions>;

  constructor(options: VersionCheckOptions = {}) {
    this.options = {
      checkInterval: options.checkInterval || 5 * 60 * 1000, // 5 minutes
      autoReload: options.autoReload ?? true,
      notifyUser: options.notifyUser ?? true,
      reloadDelay: options.reloadDelay || 5000 // 5 seconds
    };
    
    this.initialize();
  }

  private async initialize() {
    // Get initial version from meta tags
    this.currentVersion = this.getVersionFromMeta();
    
    // Start periodic checks
    this.startChecking();
    
    // Check on visibility change
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        this.checkVersion();
      }
    });
    
    // Check on online event
    window.addEventListener('online', () => {
      this.checkVersion();
    });
  }

  private getVersionFromMeta(): VersionInfo | null {
    const getMetaContent = (name: string) => {
      const meta = document.querySelector(`meta[name="${name}"]`);
      return meta?.getAttribute('content') || '';
    };
    
    const version = getMetaContent('build-version');
    const buildId = getMetaContent('build-id');
    const buildTime = getMetaContent('build-time');
    const integrity = getMetaContent('build-integrity');
    
    if (!buildId) {
      console.warn('No build version information found in meta tags');
      return null;
    }
    
    return { version, buildId, buildTime, integrity };
  }

  private async fetchLatestVersion(): Promise<VersionInfo | null> {
    try {
      // Use the same origin as the current page to handle different ports correctly
      const baseUrl = window.location.origin;
      const versionUrl = `${baseUrl}/version.json?t=${Date.now()}`;
      
      const response = await fetch(versionUrl, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      
      if (!response.ok) {
        console.warn(`Version check failed: ${response.status} at ${versionUrl}`);
        // Return current version to prevent false update notifications
        return this.currentVersion;
      }
      
      return await response.json();
    } catch (error) {
      console.warn('Version check skipped:', error);
      // Return current version to prevent false update notifications
      return this.currentVersion;
    }
  }

  private compareVersions(current: VersionInfo, latest: VersionInfo): boolean {
    // Compare build IDs (most reliable)
    if (current.buildId !== latest.buildId) {
      return true;
    }
    
    // Compare integrity hashes
    if (current.integrity && latest.integrity && current.integrity !== latest.integrity) {
      return true;
    }
    
    // Compare timestamps
    if (current.buildTime && latest.buildTime) {
      const currentTime = new Date(current.buildTime).getTime();
      const latestTime = new Date(latest.buildTime).getTime();
      if (latestTime > currentTime) {
        return true;
      }
    }
    
    return false;
  }

  private scheduleReload() {
    if (this.reloadScheduled) {
      return;
    }
    
    this.reloadScheduled = true;
    
    if (this.options.notifyUser) {
      showNotification({
        type: 'info',
        title: 'Update Available',
        message: `A new version is available. The page will reload in ${this.options.reloadDelay / 1000} seconds...`,
        duration: this.options.reloadDelay
      });
    }
    
    setTimeout(() => {
      this.forceReload();
    }, this.options.reloadDelay);
  }

  private forceReload() {
    // Clear all caches
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
    }
    
    // Clear session storage
    sessionStorage.clear();
    
    // Clear Vite's module cache
    if ('__vite_plugin_react_preamble_installed__' in window) {
      delete (window as any).__vite_plugin_react_preamble_installed__;
    }
    
    // Force hard reload
    window.location.reload();
  }

  public async checkVersion(): Promise<boolean> {
    if (this.isChecking || !this.currentVersion) {
      return false;
    }
    
    this.isChecking = true;
    
    try {
      const latestVersion = await this.fetchLatestVersion();
      
      if (!latestVersion) {
        return false;
      }
      
      const needsUpdate = this.compareVersions(this.currentVersion, latestVersion);
      
      if (needsUpdate) {
        console.log('Version mismatch detected:', {
          current: this.currentVersion,
          latest: latestVersion
        });
        
        if (this.options.autoReload) {
          this.scheduleReload();
        } else if (this.options.notifyUser) {
          showNotification({
            type: 'warning',
            title: 'Update Available',
            message: 'A new version is available. Please refresh the page to get the latest updates.',
            duration: 0, // Don't auto-hide
            action: {
              label: 'Refresh Now',
              onClick: () => this.forceReload()
            }
          });
        }
        
        return true;
      }
      
      return false;
    } finally {
      this.isChecking = false;
    }
  }

  public startChecking() {
    if (this.checkTimer) {
      return;
    }
    
    // Initial check after a longer delay to let everything load
    setTimeout(() => this.checkVersion(), 60000); // 60 seconds (1 minute)
    
    // Periodic checks
    this.checkTimer = setInterval(() => {
      this.checkVersion();
    }, this.options.checkInterval);
  }

  public stopChecking() {
    if (this.checkTimer) {
      clearInterval(this.checkTimer);
      this.checkTimer = null;
    }
  }

  public getVersion(): VersionInfo | null {
    return this.currentVersion;
  }

  public destroy() {
    this.stopChecking();
  }
}

// Singleton instance
let versionChecker: VersionChecker | null = null;

export function initializeVersionChecker(options?: VersionCheckOptions): VersionChecker {
  if (!versionChecker) {
    versionChecker = new VersionChecker(options);
  }
  return versionChecker;
}

export function getVersionChecker(): VersionChecker | null {
  return versionChecker;
}

export function checkForUpdates(): Promise<boolean> {
  if (versionChecker) {
    return versionChecker.checkVersion();
  }
  return Promise.resolve(false);
}

export { VersionChecker, type VersionInfo, type VersionCheckOptions };