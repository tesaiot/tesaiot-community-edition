/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  certificateManagementService,
  Certificate,
  CertificateStats,
  CertificateRenewalOptions,
} from '../services/certificateManagementService';

interface UseCertificateManagementReturn {
  // Data
  certificates: Certificate[];
  stats: CertificateStats;
  expiringCertificates: Certificate[];
  expiredCertificates: Certificate[];
  
  // Loading states
  loading: boolean;
  renewalLoading: boolean;
  
  // Actions
  refreshCertificates: () => Promise<void>;
  renewCertificate: (deviceId: string, options: CertificateRenewalOptions) => Promise<boolean>;
  revokeCertificate: (deviceId: string) => Promise<boolean>;
  downloadCertificate: (deviceId: string, fileType: 'ca-chain' | 'device-cert' | 'device-key' | 'bundle') => Promise<boolean>;
  validateCertificate: (certificate: Certificate) => {
    isValid: boolean;
    isExpiring: boolean;
    needsAttention: boolean;
    message: string;
  };
  
  // Utilities
  getCertificatesByStatus: (status: Certificate['status']) => Certificate[];
  getDeviceCertificate: (deviceId: string) => Certificate | undefined;
}

export function useCertificateManagement(): UseCertificateManagementReturn {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [stats, setStats] = useState<CertificateStats>({
    total: 0,
    active: 0,
    expiring: 0,
    expired: 0,
    revoked: 0,
  });
  const [expiringCertificates, setExpiringCertificates] = useState<Certificate[]>([]);
  const [expiredCertificates, setExpiredCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(false);
  const [renewalLoading, setRenewalLoading] = useState(false);

  // Load certificates and calculate derived data
  const loadCertificates = useCallback(async () => {
    try {
      setLoading(true);
      
      const [certificatesData, statsData, expiringData, expiredData] = await Promise.all([
        certificateManagementService.getCertificates(),
        certificateManagementService.getCertificateStats(),
        certificateManagementService.getExpiringCertificates(),
        certificateManagementService.getExpiredCertificates(),
      ]);

      setCertificates(certificatesData);
      setStats(statsData);
      setExpiringCertificates(expiringData);
      setExpiredCertificates(expiredData);
    } catch (error) {
      console.error('Error loading certificates:', error);
      toast.error('Failed to load certificate data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize data on mount
  useEffect(() => {
    loadCertificates();
  }, [loadCertificates]);

  // Refresh certificates
  const refreshCertificates = useCallback(async () => {
    await loadCertificates();
  }, [loadCertificates]);

  // Renew certificate
  const renewCertificate = useCallback(async (
    deviceId: string,
    options: CertificateRenewalOptions
  ): Promise<boolean> => {
    try {
      setRenewalLoading(true);
      const result = await certificateManagementService.renewCertificate(deviceId, options);
      
      if (result.success) {
        // Refresh certificates after successful renewal
        await refreshCertificates();
        return true;
      } else {
        toast.error(result.error || 'Certificate renewal failed');
        return false;
      }
    } catch (error) {
      console.error('Error renewing certificate:', error);
      toast.error('Certificate renewal failed');
      return false;
    } finally {
      setRenewalLoading(false);
    }
  }, [refreshCertificates]);

  // Revoke certificate
  const revokeCertificate = useCallback(async (deviceId: string): Promise<boolean> => {
    try {
      const result = await certificateManagementService.revokeCertificate(deviceId);
      
      if (result.success) {
        // Refresh certificates after successful revocation
        await refreshCertificates();
        return true;
      } else {
        toast.error(result.error || 'Certificate revocation failed');
        return false;
      }
    } catch (error) {
      console.error('Error revoking certificate:', error);
      toast.error('Certificate revocation failed');
      return false;
    }
  }, [refreshCertificates]);

  // Download certificate
  const downloadCertificate = useCallback(async (
    deviceId: string,
    fileType: 'ca-chain' | 'device-cert' | 'device-key' | 'bundle'
  ): Promise<boolean> => {
    try {
      const result = await certificateManagementService.downloadCertificateFile(deviceId, fileType);
      return result.success;
    } catch (error) {
      console.error('Error downloading certificate:', error);
      toast.error('Certificate download failed');
      return false;
    }
  }, []);

  // Validate certificate
  const validateCertificate = useCallback((certificate: Certificate) => {
    return certificateManagementService.validateCertificate(certificate);
  }, []);

  // Get certificates by status
  const getCertificatesByStatus = useCallback((status: Certificate['status']) => {
    return certificates.filter(cert => cert.status === status);
  }, [certificates]);

  // Get certificate for specific device
  const getDeviceCertificate = useCallback((deviceId: string) => {
    return certificates.find(cert => cert.deviceId === deviceId);
  }, [certificates]);

  return {
    // Data
    certificates,
    stats,
    expiringCertificates,
    expiredCertificates,
    
    // Loading states
    loading,
    renewalLoading,
    
    // Actions
    refreshCertificates,
    renewCertificate,
    revokeCertificate,
    downloadCertificate,
    validateCertificate,
    
    // Utilities
    getCertificatesByStatus,
    getDeviceCertificate,
  };
}