/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { toast } from 'sonner';
import authFetch from '@/utils/auth-fetch';

export interface Certificate {
  id: string;
  deviceId: string;
  deviceName: string;
  deviceType: string;
  status: 'active' | 'expiring' | 'expired' | 'revoked';
  issuedAt: string;
  expiresAt: string;
  daysUntilExpiry: number;
  serialNumber: string;
  algorithm: string;
  organization?: string;
}

export interface CertificateRenewalOptions {
  algorithm: string;
  keySize: string;
  validityPeriod: string;
  autoDownload: boolean;
  revokeOld: boolean;
}

export interface CertificateStats {
  total: number;
  active: number;
  expiring: number;
  expired: number;
  revoked: number;
}

/**
 * Enhanced Certificate Management Service with comprehensive error handling
 */
export class CertificateManagementService {
  private static instance: CertificateManagementService;
  private readonly baseUrl = '/api/v1/certificates';

  static getInstance(): CertificateManagementService {
    if (!CertificateManagementService.instance) {
      CertificateManagementService.instance = new CertificateManagementService();
    }
    return CertificateManagementService.instance;
  }

  /**
   * Get all certificates for the current organization
   */
  async getCertificates(): Promise<Certificate[]> {
    try {
      const response = await authFetch(`${this.baseUrl}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch certificates: ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformCertificateData(data.certificates || data || []);
    } catch (error) {
      console.error('Error fetching certificates:', error);
      toast.error('Failed to load certificates');
      return [];
    }
  }

  /**
   * Get certificate statistics
   */
  async getCertificateStats(): Promise<CertificateStats> {
    try {
      const certificates = await this.getCertificates();
      return this.calculateStats(certificates);
    } catch (error) {
      console.error('Error calculating certificate stats:', error);
      return { total: 0, active: 0, expiring: 0, expired: 0, revoked: 0 };
    }
  }

  /**
   * Renew a certificate
   */
  async renewCertificate(
    deviceId: string,
    options: CertificateRenewalOptions
  ): Promise<{ success: boolean; certificate?: any; error?: string }> {
    try {
      const response = await authFetch(`${this.baseUrl}/${deviceId}/renew`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          algorithm: options.algorithm,
          validity_period: parseInt(options.validityPeriod),
          revoke_old: options.revokeOld,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Certificate renewal failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (options.autoDownload && data.certificate) {
        await this.downloadCertificateBundle(deviceId);
      }

      toast.success('Certificate renewed successfully');
      return { success: true, certificate: data.certificate };
    } catch (error) {
      console.error('Certificate renewal error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast.error(`Certificate renewal failed: ${errorMessage}`);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Revoke a certificate
   */
  async revokeCertificate(deviceId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await authFetch(`${this.baseUrl}/${deviceId}/revoke`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Certificate revocation failed: ${response.statusText}`);
      }

      toast.success('Certificate revoked successfully');
      return { success: true };
    } catch (error) {
      console.error('Certificate revocation error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast.error(`Certificate revocation failed: ${errorMessage}`);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Download certificate file
   */
  async downloadCertificateFile(
    deviceId: string,
    fileType: 'ca-chain' | 'device-cert' | 'device-key' | 'bundle'
  ): Promise<{ success: boolean; error?: string }> {
    try {
      console.log('[CertificateManagement] Initiating download', { deviceId, fileType });

      const downloadUrl = `/api/v1/certificates/devices/${deviceId}/certificate/download/${fileType}`;
      const response = await authFetch(downloadUrl, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Failed to download ${fileType}: ${response.statusText}`);
      }

      const blob = await response.blob();
      console.log('[CertificateManagement] Download response', {
        fileType,
        size: blob.size,
        contentType: response.headers.get('Content-Type'),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.style.display = 'none';
      a.rel = 'noopener';

      // Prefer server-provided filename; fallback per file type
      const cd = response.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      let filename = '';
      if (match) {
        filename = decodeURIComponent((match[1] || match[2] || '').trim());
      }
      if (!filename) {
        if (fileType === 'bundle') {
          const ts = new Date().toISOString().replace(/:/g, '-').split('.')[0];
          filename = `${deviceId}-mqtts-mtls-bundle-${ts}.zip`;
        } else if (fileType === 'device-key') {
          filename = `${deviceId}-private-key.pem`;
        } else if (fileType === 'device-cert') {
          filename = `${deviceId}-certificate.pem`;
        } else if (fileType === 'ca-chain') {
          filename = `${deviceId}-ca-chain.pem`;
        } else {
          filename = `${deviceId}-${fileType}`;
        }
      }
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);

      // Extra safeguard: open in new tab if click suppressed (Safari)
      if (!blob.size) {
        window.open(url, '_blank');
      }

      toast.success(`${fileType} downloaded successfully`);
      return { success: true };
    } catch (error) {
      console.error('Certificate download error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast.error(`Failed to download ${fileType}: ${errorMessage}`);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Download certificate bundle
   */
  async downloadCertificateBundle(deviceId: string): Promise<{ success: boolean; error?: string }> {
    return this.downloadCertificateFile(deviceId, 'bundle');
  }

  /**
   * Validate certificate status
   */
  validateCertificate(certificate: Certificate): {
    isValid: boolean;
    isExpiring: boolean;
    needsAttention: boolean;
    message: string;
  } {
    if (certificate.status === 'revoked') {
      return {
        isValid: false,
        isExpiring: false,
        needsAttention: true,
        message: 'Certificate has been revoked'
      };
    }

    if (certificate.daysUntilExpiry < 0) {
      return {
        isValid: false,
        isExpiring: false,
        needsAttention: true,
        message: `Certificate expired ${Math.abs(certificate.daysUntilExpiry)} days ago`
      };
    }

    if (certificate.daysUntilExpiry <= 30) {
      return {
        isValid: true,
        isExpiring: true,
        needsAttention: true,
        message: `Certificate expires in ${certificate.daysUntilExpiry} days`
      };
    }

    return {
      isValid: true,
      isExpiring: false,
      needsAttention: false,
      message: `Certificate is valid for ${certificate.daysUntilExpiry} more days`
    };
  }

  /**
   * Get expiring certificates
   */
  async getExpiringCertificates(daysThreshold: number = 30): Promise<Certificate[]> {
    try {
      const certificates = await this.getCertificates();
      return certificates.filter(cert => 
        cert.daysUntilExpiry <= daysThreshold && cert.daysUntilExpiry > 0
      );
    } catch (error) {
      console.error('Error fetching expiring certificates:', error);
      return [];
    }
  }

  /**
   * Get expired certificates
   */
  async getExpiredCertificates(): Promise<Certificate[]> {
    try {
      const certificates = await this.getCertificates();
      return certificates.filter(cert => cert.daysUntilExpiry < 0);
    } catch (error) {
      console.error('Error fetching expired certificates:', error);
      return [];
    }
  }

  /**
   * Transform API response to Certificate interface
   */
  private transformCertificateData(apiData: any[]): Certificate[] {
    return apiData.map(item => ({
      id: item.id || item._id || item.certificate_id,
      deviceId: item.device_id || item.deviceId,
      deviceName: item.device_name || item.deviceName || item.name,
      deviceType: item.device_type || item.deviceType || item.type || 'unknown',
      status: this.mapCertificateStatus(item),
      issuedAt: item.issued_at || item.issuedAt || item.created_at,
      expiresAt: item.expires_at || item.expiresAt || item.expiry_date,
      daysUntilExpiry: this.calculateDaysUntilExpiry(item.expires_at || item.expiresAt || item.expiry_date),
      serialNumber: item.serial_number || item.serialNumber || item.serial,
      algorithm: item.algorithm || item.key_algorithm || 'RSA-2048',
      organization: item.organization || item.org_name,
    }));
  }

  /**
   * Map API certificate status to our status enum
   */
  private mapCertificateStatus(item: any): Certificate['status'] {
    const status = item.status || item.certificate_status;
    const daysUntilExpiry = this.calculateDaysUntilExpiry(
      item.expires_at || item.expiresAt || item.expiry_date
    );

    if (status === 'revoked') return 'revoked';
    if (daysUntilExpiry < 0) return 'expired';
    if (daysUntilExpiry <= 30) return 'expiring';
    return 'active';
  }

  /**
   * Calculate days until certificate expiry
   */
  private calculateDaysUntilExpiry(expiryDate: string): number {
    if (!expiryDate) return 0;
    const now = new Date();
    const expiry = new Date(expiryDate);
    const diffTime = expiry.getTime() - now.getTime();
    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
  }

  /**
   * Calculate certificate statistics
   */
  private calculateStats(certificates: Certificate[]): CertificateStats {
    return certificates.reduce(
      (stats, cert) => {
        stats.total++;
        stats[cert.status]++;
        return stats;
      },
      { total: 0, active: 0, expiring: 0, expired: 0, revoked: 0 }
    );
  }
}

export const certificateManagementService = CertificateManagementService.getInstance();
