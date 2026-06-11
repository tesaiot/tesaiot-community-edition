/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Certificate Management API Service
 *
 * Handles all API operations for PKI and certificate lifecycle management
 * Extracted from tesaApi.ts (lines 661-1263) as part of Phase 2 refactoring
 *
 * @module CertificateManagementApiService
 */

import { AxiosInstance } from 'axios';
import type {
  Certificate,
  CertificateHealthResponse,
  AutoRenewalSettings,
  AutoRenewalTriggerResponse,
  TestNotificationRequest,
  BulkCertificateOperationRequest,
  BulkCertificateOperationResponse,
  CertificateAnalyticsResponse,
  CSRValidationResponse,
  CertificateGenerationRequest,
  CertificateGenerationResponse,
  CSRSigningRequest,
  CSRSigningResponse,
  CertificateDownloadOptions,
  CertificateChainVerificationResponse,
  CaChainHealthResponse,
  CertificateUsageStatsResponse,
  AcmeDirectoryResponse,
  AcmeAccountCreationRequest,
  AcmeAccountCreationResponse,
  AcmeOrderCreationResponse,
  AcmeOrderFinalizationResponse,
  AcmeCertificateDownloadResponse,
  AcmeSettings
} from '../types/certificateManagement.types';

/**
 * CertificateManagementApiService
 *
 * Provides comprehensive PKI operations:
 * - Certificate CRUD (create, read, renew, revoke)
 * - Health monitoring and analytics
 * - Auto-renewal management
 * - CSR validation and signing
 * - ACME protocol support
 * - Bulk operations and audit trails
 *
 * @example
 * ```typescript
 * const service = new CertificateManagementApiService(axiosInstance);
 * const certs = await service.getCertificates();
 * const health = await service.getCertificateHealth();
 * ```
 */
export class CertificateManagementApiService {
  constructor(private api: AxiosInstance) {}

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Certificate CRUD Operations
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Get all certificates
   */
  async getCertificates(): Promise<Certificate[]> {
    const response = await this.api.get('/api/v1/certificates');
    return response.data;
  }

  /**
   * Revoke a certificate by ID
   */
  async revokeCertificate(id: string): Promise<void> {
    await this.api.post(`/api/v1/certificates/${id}/revoke`);
  }

  /**
   * Renew certificate for a device
   */
  async renewCertificate(deviceId: string): Promise<Certificate> {
    const response = await this.api.post(`/api/v1/certificates/devices/${deviceId}/certificate/renew`);
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Health & Analytics
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Get certificate health metrics
   */
  async getCertificateHealth(): Promise<CertificateHealthResponse> {
    const response = await this.api.get('/api/v1/certificates/health');
    return response.data;
  }

  /**
   * Get certificate analytics with trends and recommendations
   */
  async getCertificateAnalytics(): Promise<CertificateAnalyticsResponse> {
    const response = await this.api.get('/api/v1/certificates/analytics');
    return response.data;
  }

  /**
   * Get certificate usage statistics
   */
  async getCertificateUsageStats(): Promise<CertificateUsageStatsResponse> {
    const response = await this.api.get('/api/v1/certificates/usage-stats');
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Auto-Renewal Management
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Get auto-renewal settings
   */
  async getAutoRenewalSettings(): Promise<AutoRenewalSettings> {
    const response = await this.api.get('/api/v1/certificates/auto-renewal');
    return response.data;
  }

  /**
   * Update auto-renewal settings
   */
  async updateAutoRenewalSettings(settings: Omit<AutoRenewalSettings, 'vault_role' | 'template'>): Promise<any> {
    const response = await this.api.post('/api/v1/certificates/auto-renewal', settings);
    return response.data;
  }

  /**
   * Trigger auto-renewal manually
   */
  async triggerAutoRenewal(): Promise<AutoRenewalTriggerResponse> {
    const response = await this.api.post('/api/v1/certificates/auto-renewal/trigger');
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Notifications & Audit
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Test notification (email or webhook)
   */
  async testNotification(type: 'email' | 'webhook', data: TestNotificationRequest): Promise<any> {
    const response = await this.api.post('/api/v1/certificates/test-notification', {
      type,
      ...data
    });
    return response.data;
  }

  /**
   * Get certificate audit trail
   */
  async getCertificateAuditTrail(): Promise<any[]> {
    const response = await this.api.get('/api/v1/certificates/audit-trail');
    return response.data;
  }

  /**
   * Export certificate audit trail
   */
  async exportCertificateAuditTrail(): Promise<any> {
    const response = await this.api.get('/api/v1/certificates/audit-trail/export');
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Bulk Operations
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Perform bulk certificate operation
   */
  async bulkCertificateOperation(data: BulkCertificateOperationRequest): Promise<BulkCertificateOperationResponse> {
    const response = await this.api.post('/api/v1/certificates/bulk', data);
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // CSR Validation & Certificate Generation
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Validate a Certificate Signing Request (CSR)
   */
  async validateCSR(csrContent: string): Promise<CSRValidationResponse> {
    const response = await this.api.post('/api/v1/certificates/validate-csr', {
      csr: csrContent
    });
    return response.data;
  }

  /**
   * Generate a certificate for a device
   */
  async generateDeviceCertificate(request: CertificateGenerationRequest): Promise<CertificateGenerationResponse> {
    try {
      const response = await this.api.post('/api/v1/certificates/generate', request);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new Error(`Invalid certificate generation request: ${error.response.data?.message || 'Bad request'}`);
      }
      if (error.response?.status === 404) {
        throw new Error(`Device not found: ${request.deviceId}`);
      }
      if (error.response?.status === 409) {
        throw new Error(`Certificate already exists for device: ${request.deviceId}`);
      }
      if (error.response?.status === 422) {
        if (request.encrypted && !request.encryptionKeyId) {
          throw new Error('Encryption key ID is required for encrypted certificate generation');
        }
        throw new Error(`Certificate generation validation failed: ${error.response.data?.message || 'Validation error'}`);
      }
      throw new Error(`Failed to generate device certificate: ${error.message}`);
    }
  }

  /**
   * Sign a CSR and generate certificate
   */
  async signCSR(request: CSRSigningRequest): Promise<CSRSigningResponse> {
    try {
      const response = await this.api.post('/api/v1/certificates/sign-csr', request);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new Error(`Invalid CSR: ${error.response.data?.message || 'Bad request'}`);
      }
      if (error.response?.status === 404) {
        throw new Error(`Device not found: ${request.deviceId}`);
      }
      if (error.response?.status === 422) {
        if (request.encrypted && !request.encryptionKeyId) {
          throw new Error('Encryption key ID is required for encrypted certificate signing');
        }
        throw new Error(`CSR validation failed: ${error.response.data?.message || 'Validation error'}`);
      }
      throw new Error(`Failed to sign CSR: ${error.message}`);
    }
  }

  /**
   * Download device certificate
   */
  async downloadDeviceCertificate(deviceId: string, options?: CertificateDownloadOptions): Promise<void> {
    try {
      const params: any = {};
      if (options?.format) params.format = options.format;
      if (options?.includeChain !== undefined) params.includeChain = options.includeChain;
      if (options?.encrypted !== undefined) params.encrypted = options.encrypted;
      if (options?.encryptionKeyId) params.encryptionKeyId = options.encryptionKeyId;

      const response = await this.api.get(`/api/v1/devices/${deviceId}/certificate/download`, {
        params,
        responseType: 'blob'
      });

      // Create download link
      const blob = new Blob([response.data], {
        type: options?.format === 'der' ? 'application/x-x509-ca-cert' : 'application/x-pem-file'
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      const ext = options?.format || 'pem';
      link.download = `device-${deviceId}-certificate.${ext}`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      throw new Error(`Failed to download certificate: ${error.message}`);
    }
  }

  /**
   * Download CA certificate chain for Server-TLS authentication
   */
  async downloadCaCertificate(): Promise<void> {
    try {
      const response = await this.api.get('/api/v1/certificates/ca-chain', {
        responseType: 'blob'
      });

      // Create download link
      const blob = new Blob([response.data], { type: 'application/x-pem-file' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'tesa-ca-chain.pem';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      throw new Error(`Failed to download CA certificate: ${error.message}`);
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Certificate Chain Verification
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Verify certificate chain for a device
   */
  async verifyCertificateChain(deviceId: string): Promise<CertificateChainVerificationResponse> {
    const response = await this.api.get(`/api/v1/devices/${deviceId}/certificate/verify`);
    return response.data;
  }

  /**
   * Get CA chain health status
   */
  async getCaChainHealth(): Promise<CaChainHealthResponse> {
    const response = await this.api.get('/api/v1/certificates/ca-chain/health');
    return response.data;
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // ACME Protocol Support
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Get ACME directory endpoints
   */
  async getAcmeDirectory(): Promise<AcmeDirectoryResponse> {
    const response = await this.api.get('/api/v1/acme/directory');
    return response.data;
  }

  /**
   * Create ACME account
   */
  async createAcmeAccount(data: AcmeAccountCreationRequest): Promise<AcmeAccountCreationResponse> {
    const response = await this.api.post('/api/v1/acme/new-account', data);
    return response.data;
  }

  /**
   * Create ACME order for certificate
   */
  async createAcmeOrder(accountId: string, identifiers: Array<{ type: string; value: string }>): Promise<AcmeOrderCreationResponse> {
    const response = await this.api.post('/api/v1/acme/new-order',
      { identifiers },
      { headers: { 'X-ACME-Account-ID': accountId } }
    );
    return response.data;
  }

  /**
   * Finalize ACME order with CSR
   */
  async finalizeAcmeOrder(orderId: string, csr: string): Promise<AcmeOrderFinalizationResponse> {
    const response = await this.api.post(`/api/v1/acme/orders/${orderId}/finalize`, { csr });
    return response.data;
  }

  /**
   * Download ACME certificate (plain or encrypted)
   */
  async downloadAcmeCertificate(
    certificateId: string,
    encrypted?: boolean,
    encryptionKeyId?: string
  ): Promise<AcmeCertificateDownloadResponse> {
    const params: any = {};
    if (encrypted !== undefined) {
      params.encrypted = encrypted;
    }
    if (encryptionKeyId) {
      params.encryptionKeyId = encryptionKeyId;
    }

    const response = await this.api.get(`/api/v1/acme/certificates/${certificateId}`, {
      params,
      responseType: encrypted ? 'json' : 'text'
    });

    return response.data;
  }

  /**
   * Get ACME settings
   */
  async getAcmeSettings(): Promise<AcmeSettings> {
    const response = await this.api.get('/api/v1/certificates/acme/settings');
    return response.data;
  }

  /**
   * Update ACME settings
   */
  async updateAcmeSettings(settings: Omit<AcmeSettings, 'directory_url'>): Promise<any> {
    const response = await this.api.post('/api/v1/certificates/acme/settings', settings);
    return response.data;
  }
}
