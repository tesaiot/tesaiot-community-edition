/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect, useCallback } from 'react';
import { tesaApi, Certificate } from '@/services/api/tesaApi';
import { toast } from 'sonner';

export const useCertificates = () => {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCert, setSelectedCert] = useState<Certificate | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  const loadCertificates = useCallback(async () => {
    try {
      setLoading(true);
      const data = await tesaApi.getCertificates();
      setCertificates(data);
    } catch (error) {
      toast.error('Error', {
        description: 'Failed to load certificates'
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRevokeCertificate = useCallback(async (cert: Certificate) => {
    if (confirm(`Are you sure you want to revoke this certificate?`)) {
      try {
        await tesaApi.revokeCertificate(cert.id);
        toast.success('Success', {
          description: 'Certificate revoked successfully'
        });
        loadCertificates();
      } catch (error) {
        toast.error('Error', {
          description: 'Failed to revoke certificate'
        });
      }
    }
  }, [loadCertificates]);

  const handleRenewCertificate = useCallback(async (certOrDeviceId: Certificate | string) => {
    try {
      const deviceId = typeof certOrDeviceId === 'string' ? certOrDeviceId : certOrDeviceId.deviceId;
      await tesaApi.renewCertificate(deviceId);
      toast.success('Success', {
        description: 'Certificate renewed successfully'
      });
      loadCertificates();
    } catch (error) {
      toast.error('Error', {
        description: 'Failed to renew certificate'
      });
    }
  }, [loadCertificates]);

  const handleViewDetails = useCallback((cert: Certificate) => {
    setSelectedCert(cert);
    setDetailsOpen(true);
  }, []);

  const handleExportCertificate = useCallback(async (cert: Certificate) => {
    try {
      const token = localStorage.getItem('jwt_token');
      const url = `/api/v1/certificates/devices/${cert.deviceId}/certificate/download/bundle`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      // Use filename from server when provided
      const cd = response.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      let filename = '';
      if (match) {
        filename = decodeURIComponent((match[1] || match[2] || '').trim());
      }
      if (!filename) {
        const ts = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        filename = `${cert.deviceId}-mqtts-mtls-bundle-${ts}.zip`;
      }
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success('Certificate Bundle Downloaded', {
        description: 'Certificate bundle downloaded successfully'
      });
    } catch (error) {
      toast.error('Download Failed', {
        description: 'Failed to download certificate bundle'
      });
    }
  }, []);

  const getDaysUntilExpiry = useCallback((validTo: string) => {
    const expiry = new Date(validTo);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  }, []);

  const filteredCertificates = certificates.filter(cert => {
    const matchesSearch = 
      cert.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.issuer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.fingerprint.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'expiring') {
      const days = getDaysUntilExpiry(cert.validTo);
      return matchesSearch && days >= 0 && days <= 30;
    }
    return matchesSearch && cert.status === activeTab;
  });

  const certStats = {
    total: certificates.length,
    active: certificates.filter(c => c.status === 'active').length,
    expiring: certificates.filter(c => {
      const days = getDaysUntilExpiry(c.validTo);
      return c.status === 'active' && days >= 0 && days <= 30;
    }).length,
    expired: certificates.filter(c => c.status === 'expired').length,
    revoked: certificates.filter(c => c.status === 'revoked').length,
  };

  useEffect(() => {
    loadCertificates();
  }, [loadCertificates]);

  return {
    certificates,
    loading,
    searchTerm,
    setSearchTerm,
    selectedCert,
    setSelectedCert,
    detailsOpen,
    setDetailsOpen,
    activeTab,
    setActiveTab,
    loadCertificates,
    handleRevokeCertificate,
    handleRenewCertificate,
    handleViewDetails,
    handleExportCertificate,
    getDaysUntilExpiry,
    filteredCertificates,
    certStats
  };
};
