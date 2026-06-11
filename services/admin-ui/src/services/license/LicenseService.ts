/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// License Service for managing platform licensing and feature availability

import { 
  License, 
  LicenseEdition, 
  LicenseFeatures, 
  LicenseLimits,
  EDITION_FEATURES,
  EDITION_LIMITS 
} from './types';

export class LicenseService {
  private static instance: LicenseService;
  private currentLicense: License | null = null;
  private licenseCheckInterval: NodeJS.Timeout | null = null;
  private isLoadingLicense: boolean = false;
  private lastLoadTime: number = 0;

  private constructor() {
    // Private constructor for singleton
    this.loadLicense();
    this.startLicenseCheck();
  }

  static getInstance(): LicenseService {
    if (!LicenseService.instance) {
      LicenseService.instance = new LicenseService();
    }
    return LicenseService.instance;
  }

  /**
   * Load license from backend or local storage
   */
  private async loadLicense(): Promise<void> {
    // Prevent multiple simultaneous loads
    if (this.isLoadingLicense) return;
    
    // Rate limit license loading (minimum 1 second between loads)
    const now = Date.now();
    if (now - this.lastLoadTime < 1000) return;
    
    this.isLoadingLicense = true;
    this.lastLoadTime = now;
    
    try {
      // Try to fetch from backend
      const response = await fetch('/api/v1/license', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const licenseData = await response.json();
        const newLicense = this.parseLicense(licenseData);
        
        // Only update if actually different
        if (JSON.stringify(newLicense) !== JSON.stringify(this.currentLicense)) {
          this.currentLicense = newLicense;
          this.saveLicenseToStorage(this.currentLicense);
        }
      } else {
        // Fallback to stored license only if we don't have a current license
        if (!this.currentLicense) {
          this.loadLicenseFromStorage();
        }
      }
    } catch (error) {
      console.error('Failed to load license from server:', error);
      // Fallback to stored license only if we don't have a current license
      if (!this.currentLicense) {
        this.loadLicenseFromStorage();
      }
    } finally {
      this.isLoadingLicense = false;
    }
  }

  /**
   * Parse raw license data
   */
  private parseLicense(data: any): License {
    const edition = data.edition || 'community';
    const features = { ...EDITION_FEATURES[edition as LicenseEdition] };
    const limits = { ...EDITION_LIMITS[edition as LicenseEdition] };

    // Override with custom features if provided
    if (data.features) {
      Object.assign(features, data.features);
    }

    // Override with custom limits if provided
    if (data.limits) {
      Object.assign(limits, data.limits);
    }

    return {
      id: data.id || 'default',
      edition: edition as LicenseEdition,
      organizationId: data.organizationId || 'default',
      organizationName: data.organizationName || 'Default Organization',
      issuedAt: new Date(data.issuedAt || Date.now()),
      expiresAt: new Date(data.expiresAt || '2099-12-31'),
      isActive: data.isActive !== false,
      limits: limits as LicenseLimits,
      features: features as LicenseFeatures,
      metadata: data.metadata,
    };
  }

  /**
   * Save license to local storage
   */
  private saveLicenseToStorage(license: License): void {
    localStorage.setItem('tesa_license', JSON.stringify(license));
  }

  /**
   * Load license from local storage
   */
  private loadLicenseFromStorage(): void {
    const stored = localStorage.getItem('tesa_license');
    if (stored) {
      try {
        this.currentLicense = JSON.parse(stored);
      } catch (error) {
        console.error('Failed to parse stored license:', error);
        this.setDefaultLicense();
      }
    } else {
      this.setDefaultLicense();
    }
  }

  /**
   * Set default community license
   */
  private setDefaultLicense(): void {
    this.currentLicense = {
      id: 'community-default',
      edition: 'community',
      organizationId: 'default',
      organizationName: 'Community Organization',
      issuedAt: new Date(),
      expiresAt: new Date('2099-12-31'),
      isActive: true,
      limits: EDITION_LIMITS.community,
      features: EDITION_FEATURES.community as LicenseFeatures,
    };
    this.saveLicenseToStorage(this.currentLicense);
  }

  /**
   * Start periodic license check
   */
  private startLicenseCheck(): void {
    // Check license every 5 minutes
    this.licenseCheckInterval = setInterval(() => {
      this.loadLicense();
    }, 5 * 60 * 1000);
  }

  /**
   * Get current license
   */
  getLicense(): License | null {
    return this.currentLicense;
  }

  /**
   * Get license edition
   */
  getEdition(): LicenseEdition {
    return this.currentLicense?.edition || 'community';
  }

  /**
   * Check if license is active
   */
  isLicenseActive(): boolean {
    if (!this.currentLicense) return false;
    if (!this.currentLicense.isActive) return false;
    
    const now = new Date();
    return now < this.currentLicense.expiresAt;
  }

  /**
   * Check if commercial edition (startup, business, or enterprise)
   */
  isCommercialEdition(): boolean {
    const edition = this.getEdition();
    return edition === 'startup' || edition === 'business' || edition === 'enterprise';
  }

  /**
   * Alias for isCommercialEdition
   */
  isCommercial(): boolean {
    return this.isCommercialEdition();
  }

  /**
   * Check if a specific feature is available
   */
  hasFeature(feature: keyof LicenseFeatures): boolean {
    if (!this.isLicenseActive()) return false;
    return this.currentLicense?.features[feature] === true;
  }

  /**
   * Check multiple features at once
   */
  hasFeatures(...features: (keyof LicenseFeatures)[]): boolean {
    return features.every(feature => this.hasFeature(feature));
  }

  /**
   * Check if any of the features is available
   */
  hasAnyFeature(...features: (keyof LicenseFeatures)[]): boolean {
    return features.some(feature => this.hasFeature(feature));
  }

  /**
   * Get current limits
   */
  getLimits(): LicenseLimits {
    return this.currentLicense?.limits || EDITION_LIMITS.community;
  }

  /**
   * Check if within device limit
   */
  canAddDevice(currentCount: number): boolean {
    const limits = this.getLimits();
    return limits.devices === -1 || currentCount < limits.devices;
  }

  /**
   * Check if within user limit
   */
  canAddUser(currentCount: number): boolean {
    const limits = this.getLimits();
    return limits.users === -1 || currentCount < limits.users;
  }

  /**
   * Check if within organization limit
   */
  canAddOrganization(currentCount: number): boolean {
    const limits = this.getLimits();
    return limits.organizations === -1 || currentCount < limits.organizations;
  }

  /**
   * Get remaining API calls
   */
  getRemainingAPICalls(usedCalls: number): number {
    const limits = this.getLimits();
    if (limits.apiCallsPerMonth === -1) return -1;
    return Math.max(0, limits.apiCallsPerMonth - usedCalls);
  }

  /**
   * Check if data is within retention period
   */
  isDataWithinRetention(dataDate: Date): boolean {
    const limits = this.getLimits();
    if (limits.dataRetentionDays === -1) return true;
    
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - dataDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays <= limits.dataRetentionDays;
  }

  /**
   * Get available themes based on license
   */
  getAvailableThemes(): string[] {
    if (this.hasFeature('customThemes')) {
      return ['light', 'dark', 'blue', 'green', 'purple', 'red', 'orange', 'teal', 'pink', 'gray'];
    } else if (this.hasFeature('darkTheme')) {
      return ['light', 'dark'];
    } else {
      return ['light'];
    }
  }


  /**
   * Get upgrade URL for current edition
   */
  getUpgradeUrl(): string {
    const edition = this.getEdition();
    const upgradeMap: Record<LicenseEdition, string> = {
      community: '/pricing?upgrade=startup',
      startup: '/pricing?upgrade=business',
      business: '/pricing?upgrade=enterprise',
      enterprise: '/contact-sales',
    };
    return upgradeMap[edition];
  }

  /**
   * Format limit value for display
   */
  formatLimit(value: number, singular: string, plural?: string): string {
    if (value === -1) return 'Unlimited';
    if (value === 0) return `No ${plural || singular}`;
    if (value === 1) return `1 ${singular}`;
    return `${value.toLocaleString()} ${plural || singular}`;
  }

  /**
   * Destroy service (cleanup)
   */
  destroy(): void {
    if (this.licenseCheckInterval) {
      clearInterval(this.licenseCheckInterval);
      this.licenseCheckInterval = null;
    }
  }
}

// Export singleton instance
export const licenseService = LicenseService.getInstance();