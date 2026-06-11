/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { toast } from 'sonner';
import { Device } from '../types/device.types';
import { deviceService } from './deviceService';

export type CertificateFileType = 'ca-chain' | 'device-cert' | 'device-key' | 'bundle';

/**
 * Service for handling certificate operations
 */
export class CertificateService {
  /**
   * Download certificate files from Vault PKI
   */
  static async downloadCertificateFile(device: Device, fileType: CertificateFileType): Promise<void> {
    try {
      console.log(`Downloading ${fileType} for device:`, device.id);
      
      // Use actual device_id for API calls, not MongoDB ObjectId
      const deviceIdentifier = (device as any).device_id || (device as any).serialNumber || device.id;
      // Use fetch to capture Content-Disposition for accurate filename
      const resp = await deviceService.downloadCertificateResponse(deviceIdentifier, fileType);
      console.debug('[CertificateService] Download response received', {
        fileType,
        status: resp.status,
        contentType: resp.headers.get('Content-Type'),
        disposition: resp.headers.get('Content-Disposition')
      });

      if (!resp.ok) throw new Error('Download failed');

      const blob = await resp.blob();
      console.debug('[CertificateService] Blob metadata', {
        size: blob.size,
        type: blob.type
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Prefer server-provided filename
      const cd = resp.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      let filename = '';
      if (match) filename = decodeURIComponent((match[1] || match[2] || '').trim());
      // Fallback naming
      if (!filename) {
        if (fileType === 'bundle') {
          const ts = new Date().toISOString().replace(/:/g, '-').split('.')[0];
          filename = `${deviceIdentifier}-mqtts-mtls-bundle-${ts}.zip`;
        } else if (fileType === 'device-key' && device.key_encryption_enabled && (device.device_public_key?.key || device.public_key)) {
          filename = `${deviceIdentifier}-private-key-encrypted.json`;
        } else if (fileType === 'device-key') {
          filename = `${deviceIdentifier}-private-key.pem`;
        } else if (fileType === 'device-cert') {
          filename = `${deviceIdentifier}-certificate.pem`;
        } else if (fileType === 'ca-chain') {
          filename = `${deviceIdentifier}-ca-chain.pem`;
        } else {
          filename = `${deviceIdentifier}-${fileType}`;
        }
      }
      a.download = filename;
      document.body.appendChild(a);
      a.rel = 'noopener';

      try {
        a.click();
        console.debug('[CertificateService] Anchor click dispatched');
      } catch (clickError) {
        console.warn('[CertificateService] Anchor click failed, attempting fallback', clickError);
        window.open(url, '_blank', 'noopener');
      } finally {
        document.body.removeChild(a);
      }

      if (!blob.size) {
        console.warn('[CertificateService] Blob is empty, triggering fallback window.open');
        window.open(url, '_blank', 'noopener');
      }

      setTimeout(() => URL.revokeObjectURL(url), 1000);

      const successMessage = fileType === 'bundle' 
        ? 'Certificate bundle (ZIP) downloaded successfully from Vault PKI'
        : `${fileType} downloaded successfully from Vault PKI`;
      toast.success(successMessage);
    } catch (error) {
      console.error('Certificate download error:', error);
      toast.error(`Failed to download ${fileType}: Network error`);
    }
  }

  /**
   * Generate certificate for a device
   */
  static async generateCertificate(deviceId: string, options?: { algorithm?: string }): Promise<any> {
    try {
      const result = await deviceService.generateCertificate(deviceId, options);
      if (result) {
        toast.success('Certificate generated successfully');
        return result;
      } else {
        throw new Error('Failed to generate certificate');
      }
    } catch (error) {
      console.error('Certificate generation error:', error);
      toast.error('Failed to generate certificate');
      throw error;
    }
  }

  /**
   * Validate certificate status
   */
  static validateCertificate(device: Device): {
    isValid: boolean;
    isExpiring: boolean;
    daysUntilExpiry: number;
  } {
    if (!device.certificate) {
      return { isValid: false, isExpiring: false, daysUntilExpiry: 0 };
    }

    const now = new Date();
    const expiryDate = new Date(device.certificate.expiresAt);
    const daysUntilExpiry = Math.floor((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    return {
      isValid: device.certificate.status === 'active' && daysUntilExpiry > 0,
      isExpiring: daysUntilExpiry <= 30 && daysUntilExpiry > 0,
      daysUntilExpiry
    };
  }

  /**
   * Create certificate bundle for download
   */
  static createCertificateBundle(certificateData: {
    deviceId: string;
    certificate: string;
    privateKey: string;
    caChain: string;
    algorithm: string;
    format: string;
  }): any {
    return {
      deviceId: certificateData.deviceId,
      certificate: certificateData.certificate,
      privateKey: certificateData.privateKey,
      caChain: certificateData.caChain,
      algorithm: certificateData.algorithm,
      format: certificateData.format || 'pem'
    };
  }
}

export const certificateService = CertificateService;
