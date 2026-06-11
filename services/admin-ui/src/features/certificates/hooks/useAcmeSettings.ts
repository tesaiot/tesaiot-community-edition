/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect, useCallback } from 'react';
import { tesaApi } from '@/services/api/tesaApi';
import { toast } from 'sonner';

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
  challengeType: string;
}

export interface AcmeCertificate {
  domain: string;
  status: string;
  expiresAt: string;
  autoRenew: boolean;
  lastRenewal?: string;
  nextRenewal?: string;
}

export const useAcmeSettings = () => {
  const [acmeSettings, setAcmeSettings] = useState<AcmeSettings>({
    enabled: false,
    directory_url: '',
    challenge_types: ['device-identity-01'],
    certificate_validity_days: 90,
    auto_provision_enabled: false,
    external_account_required: true
  });

  const [acmeEnabled, setAcmeEnabled] = useState(false);
  const [acmeConfig, setAcmeConfig] = useState<AcmeConfig>({
    directoryUrl: '',
    contactEmail: '',
    challengeType: 'http-01'
  });

  const [acmeCertificates, setAcmeCertificates] = useState<AcmeCertificate[]>([]);
  const [loadingAcme, setLoadingAcme] = useState(false);

  const loadAcmeSettings = useCallback(async () => {
    try {
      const settings = await tesaApi.getAcmeSettings();
      setAcmeSettings(settings);
      setAcmeEnabled(settings.enabled || false);
      
      // Map to acmeConfig format with proper null checks
      setAcmeConfig({
        directoryUrl: settings.directory_url || '',
        contactEmail: settings.contact_email || '', // Use contact_email from settings
        challengeType: (settings.challenge_types && settings.challenge_types.length > 0) 
          ? settings.challenge_types[0] 
          : 'http-01'
      });
    } catch (error) {
      console.error('Failed to load ACME settings:', error);
      // Set default values on error
      setAcmeSettings({
        enabled: false,
        directory_url: 'https://acme-v02.api.letsencrypt.org/directory',
        challenge_types: ['http-01'],
        contact_email: ''
      });
      setAcmeEnabled(false);
      setAcmeConfig({
        directoryUrl: 'https://acme-v02.api.letsencrypt.org/directory',
        contactEmail: '',
        challengeType: 'http-01'
      });
    }
  }, []);

  const loadAcmeCertificates = useCallback(async () => {
    try {
      setLoadingAcme(true);
      const certs = await tesaApi.getAcmeCertificates();
      setAcmeCertificates(certs);
    } catch (error) {
      console.error('Failed to load ACME certificates:', error);
    } finally {
      setLoadingAcme(false);
    }
  }, []);

  const saveAcmeConfig = useCallback(async () => {
    try {
      await tesaApi.updateAcmeSettings({
        ...acmeSettings,
        enabled: acmeEnabled,
        directory_url: acmeConfig.directoryUrl,
        challenge_types: [acmeConfig.challengeType]
      });
      
      toast.success('ACME Configuration Saved', {
        description: 'ACME settings have been updated successfully'
      });
    } catch (error) {
      toast.error('Save Failed', {
        description: 'Failed to save ACME configuration'
      });
    }
  }, [acmeSettings, acmeEnabled, acmeConfig]);

  const toggleAutoRenew = useCallback(async (domain: string, enabled: boolean) => {
    try {
      await tesaApi.updateAcmeCertificate(domain, { autoRenew: enabled });
      
      const updatedCerts = acmeCertificates.map(cert => 
        cert.domain === domain ? { ...cert, autoRenew: enabled } : cert
      );
      setAcmeCertificates(updatedCerts);
      
      toast.success('Auto-Renewal Updated', {
        description: `Auto-renewal ${enabled ? 'enabled' : 'disabled'} for ${domain}`
      });
    } catch (error) {
      toast.error('Update Failed', {
        description: 'Failed to update auto-renewal setting'
      });
    }
  }, [acmeCertificates]);

  const renewAcmeCertificate = useCallback(async (domain: string) => {
    try {
      await tesaApi.renewAcmeCertificate(domain);
      toast.success('Certificate Renewed', {
        description: `Certificate for ${domain} has been renewed`
      });
      // Reload ACME certificates
      loadAcmeCertificates();
    } catch (error) {
      toast.error('Renewal Failed', {
        description: 'Failed to renew ACME certificate'
      });
    }
  }, [loadAcmeCertificates]);

  const addAcmeDomain = useCallback(async (domain: string) => {
    try {
      await tesaApi.addAcmeDomain({
        domain,
        contact_email: acmeConfig.contactEmail,
        challenge_type: acmeConfig.challengeType
      });
      
      toast.success('Domain Added', {
        description: `Domain ${domain} added for ACME certificate management`
      });
      
      loadAcmeCertificates();
    } catch (error) {
      toast.error('Failed to Add Domain', {
        description: 'Could not add domain for ACME management'
      });
    }
  }, [acmeConfig, loadAcmeCertificates]);

  const removeAcmeDomain = useCallback(async (domain: string) => {
    if (confirm(`Are you sure you want to remove ${domain} from ACME management?`)) {
      try {
        await tesaApi.removeAcmeDomain(domain);
        
        toast.success('Domain Removed', {
          description: `Domain ${domain} removed from ACME management`
        });
        
        loadAcmeCertificates();
      } catch (error) {
        toast.error('Failed to Remove Domain', {
          description: 'Could not remove domain from ACME management'
        });
      }
    }
  }, [loadAcmeCertificates]);

  const testAcmeConnection = useCallback(async () => {
    try {
      const result = await tesaApi.testAcmeConnection(acmeConfig.directoryUrl);
      if (result.success) {
        toast.success('Connection Successful', {
          description: 'Successfully connected to ACME provider'
        });
      } else {
        toast.error('Connection Failed', {
          description: result.error || 'Failed to connect to ACME provider'
        });
      }
    } catch (error) {
      toast.error('Connection Test Failed', {
        description: 'Could not test ACME connection'
      });
    }
  }, [acmeConfig.directoryUrl]);

  useEffect(() => {
    loadAcmeSettings();
  }, [loadAcmeSettings]);

  useEffect(() => {
    if (acmeEnabled) {
      loadAcmeCertificates();
    }
  }, [acmeEnabled, loadAcmeCertificates]);

  return {
    acmeSettings,
    setAcmeSettings,
    acmeEnabled,
    setAcmeEnabled,
    acmeConfig,
    setAcmeConfig,
    acmeCertificates,
    loadingAcme,
    loadAcmeSettings,
    loadAcmeCertificates,
    saveAcmeConfig,
    toggleAutoRenew,
    renewAcmeCertificate,
    addAcmeDomain,
    removeAcmeDomain,
    testAcmeConnection
  };
};