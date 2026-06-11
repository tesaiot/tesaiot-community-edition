/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect, useCallback } from 'react';
import { tesaApi, Certificate } from '@/services/api/tesaApi';
import { toast } from 'sonner';

interface AlertSettings {
  enabled: boolean;
  thresholds: {
    days_90: boolean;
    days_60: boolean;
    days_30: boolean;
    days_7: boolean;
  };
  emailRecipients: string[];
  webhookUrl: string;
  checkInterval: string;
  autoRenewal: {
    enabled: boolean;
    threshold: number;
    excludedDevices: string[];
    requireApproval: boolean;
    maxRetries: number;
  };
}

export const useCertificateAlerts = () => {
  const [alertSettings, setAlertSettings] = useState<AlertSettings>({
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
  });
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [alertConfigOpen, setAlertConfigOpen] = useState(false);

  const loadAlertSettings = useCallback(() => {
    const savedSettings = localStorage.getItem('certificate_alert_settings');
    if (savedSettings) {
      try {
        setAlertSettings(JSON.parse(savedSettings));
      } catch (e) {
        console.error('Failed to load alert settings:', e);
      }
    }
  }, []);

  const loadAutoRenewalSettings = useCallback(async () => {
    try {
      const settings = await tesaApi.getAutoRenewalSettings();
      setAlertSettings(prev => ({
        ...prev,
        autoRenewal: {
          enabled: settings.enabled,
          threshold: settings.threshold,
          excludedDevices: settings.excluded_devices || [],
          requireApproval: settings.require_approval,
          maxRetries: settings.max_retries
        }
      }));
    } catch (error) {
      console.error('Failed to load auto-renewal settings:', error);
    }
  }, []);

  const saveAlertSettings = useCallback(async (settings: AlertSettings) => {
    try {
      // Save to localStorage
      localStorage.setItem('certificate_alert_settings', JSON.stringify(settings));
      
      // Save auto-renewal settings to API
      if (settings.autoRenewal) {
        await tesaApi.updateAutoRenewalSettings({
          enabled: settings.autoRenewal.enabled,
          threshold: settings.autoRenewal.threshold,
          excluded_devices: settings.autoRenewal.excludedDevices,
          require_approval: settings.autoRenewal.requireApproval,
          max_retries: settings.autoRenewal.maxRetries
        });
      }
      
      setAlertSettings(settings);
      toast.success('Alert Settings Saved', {
        description: 'Certificate alert settings have been updated successfully'
      });
    } catch (error) {
      toast.error('Save Failed', {
        description: 'Failed to save alert settings'
      });
    }
  }, []);

  const addEmailRecipient = useCallback((email: string) => {
    if (email && !alertSettings.emailRecipients.includes(email)) {
      const newSettings = {
        ...alertSettings,
        emailRecipients: [...alertSettings.emailRecipients, email]
      };
      saveAlertSettings(newSettings);
    }
  }, [alertSettings, saveAlertSettings]);

  const removeEmailRecipient = useCallback((email: string) => {
    const newSettings = {
      ...alertSettings,
      emailRecipients: alertSettings.emailRecipients.filter(e => e !== email)
    };
    saveAlertSettings(newSettings);
  }, [alertSettings, saveAlertSettings]);

  const updateThreshold = useCallback((threshold: keyof AlertSettings['thresholds'], enabled: boolean) => {
    const newSettings = {
      ...alertSettings,
      thresholds: {
        ...alertSettings.thresholds,
        [threshold]: enabled
      }
    };
    saveAlertSettings(newSettings);
  }, [alertSettings, saveAlertSettings]);

  const updateAutoRenewalSettings = useCallback((updates: Partial<AlertSettings['autoRenewal']>) => {
    const newSettings = {
      ...alertSettings,
      autoRenewal: {
        ...alertSettings.autoRenewal,
        ...updates
      }
    };
    saveAlertSettings(newSettings);
  }, [alertSettings, saveAlertSettings]);

  const getExpiringCertificates = useCallback((certificates: Certificate[], daysThreshold: number = 30) => {
    return certificates.filter(cert => {
      const expiry = new Date(cert.validTo);
      const now = new Date();
      const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      return cert.status === 'active' && days >= 0 && days <= daysThreshold;
    });
  }, []);

  useEffect(() => {
    loadAlertSettings();
    loadAutoRenewalSettings();
  }, [loadAlertSettings, loadAutoRenewalSettings]);

  return {
    alertSettings,
    setAlertSettings,
    alertsEnabled,
    setAlertsEnabled,
    alertConfigOpen,
    setAlertConfigOpen,
    saveAlertSettings,
    addEmailRecipient,
    removeEmailRecipient,
    updateThreshold,
    updateAutoRenewalSettings,
    getExpiringCertificates
  };
};