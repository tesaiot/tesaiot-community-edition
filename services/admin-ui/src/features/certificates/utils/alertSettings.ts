/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface AlertThresholds {
  days_90: boolean;
  days_60: boolean;
  days_30: boolean;
  days_7: boolean;
}

export interface AutoRenewalSettings {
  enabled: boolean;
  threshold: number;
  excludedDevices: string[];
  requireApproval: boolean;
  maxRetries: number;
}

export interface AlertSettings {
  enabled: boolean;
  thresholds: AlertThresholds;
  emailRecipients: string[];
  webhookUrl: string;
  checkInterval: 'hourly' | 'daily' | 'weekly';
  autoRenewal: AutoRenewalSettings;
}

export interface AcmeSettings {
  enabled: boolean;
  directory_url: string;
  challenge_types: string[];
  certificate_validity_days: number;
  auto_provision_enabled: boolean;
  external_account_required: boolean;
}

export interface AcmeConfig {
  directoryUrl: string;
  contactEmail: string;
  challengeType: 'http-01' | 'dns-01';
}

/**
 * Default alert settings
 */
export const defaultAlertSettings: AlertSettings = {
  enabled: true,
  thresholds: {
    days_90: true,
    days_60: true,
    days_30: true,
    days_7: true
  },
  emailRecipients: [],
  webhookUrl: '',
  checkInterval: 'daily',
  autoRenewal: {
    enabled: false,
    threshold: 30,
    excludedDevices: [],
    requireApproval: false,
    maxRetries: 3
  }
};

/**
 * Default ACME settings
 */
export const defaultAcmeSettings: AcmeSettings = {
  enabled: false,
  directory_url: '',
  challenge_types: ['device-identity-01'],
  certificate_validity_days: 90,
  auto_provision_enabled: false,
  external_account_required: true
};

/**
 * Default ACME configuration
 */
export const defaultAcmeConfig: AcmeConfig = {
  directoryUrl: '',
  contactEmail: '',
  challengeType: 'http-01'
};

/**
 * Save alert settings to localStorage
 * @param settings - Alert settings to save
 */
export const saveAlertSettingsToLocalStorage = (settings: AlertSettings): void => {
  try {
    localStorage.setItem('certificate_alert_settings', JSON.stringify(settings));
  } catch (error) {
    console.error('Failed to save alert settings to localStorage:', error);
  }
};

/**
 * Load alert settings from localStorage
 * @returns Alert settings or null if not found/invalid
 */
export const loadAlertSettingsFromLocalStorage = (): AlertSettings | null => {
  try {
    const savedSettings = localStorage.getItem('certificate_alert_settings');
    if (savedSettings) {
      return JSON.parse(savedSettings);
    }
  } catch (error) {
    console.error('Failed to load alert settings from localStorage:', error);
  }
  return null;
};