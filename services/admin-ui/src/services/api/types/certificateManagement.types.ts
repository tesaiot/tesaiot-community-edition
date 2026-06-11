/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Certificate Management Types
 *
 * Type definitions for PKI operations and certificate lifecycle management
 * Extracted from tesaApi.ts as part of Phase 2 refactoring
 *
 * @module CertificateManagementTypes
 */

/**
 * Certificate entity representing a PKI certificate
 */
export interface Certificate {
  id: string;
  deviceId: string;
  deviceName?: string;
  issuer: string;
  subject: string;
  validFrom: string;
  validTo: string;
  status: 'active' | 'expired' | 'revoked' | 'expiring';
  fingerprint: string;
  serialNumber?: string;
  algorithm?: string;
  organizationId?: string;
  type?: 'device' | 'ca';
  renewable?: boolean;
}

/**
 * Certificate health check response
 */
export interface CertificateHealthResponse {
  health_score: number;
  metrics: {
    total: number;
    healthy: number;
    warning: number;
    critical: number;
    expired: number;
    expiring_in_7_days: number;
    expiring_in_30_days: number;
    expiring_in_90_days: number;
    average_days_to_expiry: number;
  };
  renewal_recommended: Certificate[];
  certificates: Certificate[];
  timestamp: string;
}

/**
 * Auto-renewal settings
 */
export interface AutoRenewalSettings {
  enabled: boolean;
  threshold: number;
  excluded_devices: string[];
  require_approval: boolean;
  max_retries: number;
  vault_role?: string;
  template?: string;
}

/**
 * Auto-renewal trigger response
 */
export interface AutoRenewalTriggerResponse {
  message: string;
  candidates_found: number;
  renewals_initiated: number;
  require_approval: boolean;
  results: Array<{
    device_id: string;
    status: string;
    error?: string;
  }>;
  timestamp: string;
}

/**
 * Test notification request
 */
export interface TestNotificationRequest {
  recipients?: string[];
  webhook_url?: string;
}

/**
 * Bulk certificate operation request
 */
export interface BulkCertificateOperationRequest {
  action: string;
  device_ids: string[];
  reason?: string;
}

/**
 * Bulk certificate operation response
 */
export interface BulkCertificateOperationResponse {
  results: Array<{
    device_id: string;
    status: string;
    error?: string;
  }>;
}

/**
 * Certificate analytics response
 */
export interface CertificateAnalyticsResponse {
  metrics: {
    velocity: {
      daily_average: number;
      weekly_average: number;
      monthly_average: number;
    };
    compliance: {
      etsi_score: number;
      iso_score: number;
      overall_score: number;
    };
    algorithms: Record<string, number>;
    renewal_efficiency: number;
    risk_factors: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
  };
  trends: {
    issuance_trend: Array<{ date: string; count: number }>;
    expiration_forecast: Array<{ period: string; count: number }>;
  };
  recommendations: Array<{
    priority: 'critical' | 'high' | 'medium' | 'low';
    category: string;
    title: string;
    description: string;
    action: string;
  }>;
  timestamp: string;
}

/**
 * CSR validation response
 */
export interface CSRValidationResponse {
  valid: boolean;
  subject: string;
  publicKey: string;
  signatureAlgorithm: string;
  errors?: string[];
}

/**
 * Certificate generation request
 */
export interface CertificateGenerationRequest {
  deviceId: string;
  commonName?: string;
  organizationName?: string;
  validityDays?: number;
  keyAlgorithm?: string;
  encrypted?: boolean;
  encryptionKeyId?: string;
}

/**
 * Certificate generation response
 */
export interface CertificateGenerationResponse {
  certificateId: string;
  certificate: string;
  privateKey?: string;
  encryptedContent?: string;
  encryptionMetadata?: {
    algorithm: string;
    keyId: string;
    iv: string;
  };
}

/**
 * CSR signing request
 */
export interface CSRSigningRequest {
  deviceId: string;
  csr: string;
  validityDays?: number;
  encrypted?: boolean;
  encryptionKeyId?: string;
}

/**
 * CSR signing response
 */
export interface CSRSigningResponse {
  certificateId: string;
  certificate: string;
  encryptedContent?: string;
  encryptionMetadata?: {
    algorithm: string;
    keyId: string;
    iv: string;
  };
}

/**
 * Certificate download options
 */
export interface CertificateDownloadOptions {
  format?: 'pem' | 'der' | 'pkcs12';
  includeChain?: boolean;
  encrypted?: boolean;
  encryptionKeyId?: string;
}

/**
 * Certificate chain verification response
 */
export interface CertificateChainVerificationResponse {
  isValid: boolean;
  issues: Array<{
    level: 'error' | 'warning' | 'info';
    message: string;
    component: 'device' | 'intermediate' | 'root';
  }>;
  expirationStatus: {
    device: 'valid' | 'expiring' | 'expired';
    intermediate: 'valid' | 'expiring' | 'expired';
    root: 'valid' | 'expiring' | 'expired';
  };
}

/**
 * CA chain health response
 */
export interface CaChainHealthResponse {
  generated_at: string;
  entries: Array<{
    label: string;
    source: string;
    subject: string;
    issuer: string;
    serial_number: string;
    signature_algorithm: string;
    public_key_algorithm: string;
    not_before: string;
    not_after: string;
    days_remaining: number;
  }>;
}

/**
 * Certificate generation method
 */
export type CertificateGenerationMethod = 'auto' | 'csr' | 'manual' | 'acme';

/**
 * Certificate type
 */
export type CertificateType = 'device' | 'ca' | 'intermediate' | 'root';

/**
 * Certificate format
 */
export type CertificateFormat = 'pem' | 'der' | 'pkcs12';

/**
 * Certificate usage statistics response
 */
export interface CertificateUsageStatsResponse {
  totalCertificates: number;
  byGenerationMethod: Record<CertificateGenerationMethod, number>;
  byType: Record<CertificateType, number>;
  byFormat: Record<CertificateFormat, number>;
  byStatus: Record<string, number>;
  recentActivity: Array<{
    action: string;
    deviceId: string;
    timestamp: Date;
    certificateId: string;
  }>;
}

// ACME Protocol Types

/**
 * ACME directory response
 */
export interface AcmeDirectoryResponse {
  newNonce: string;
  newAccount: string;
  newOrder: string;
  newAuthz: string;
  revokeCert: string;
  keyChange: string;
  meta: {
    termsOfService: string;
    website: string;
    caaIdentities: string[];
    externalAccountRequired: boolean;
  };
}

/**
 * ACME account creation request
 */
export interface AcmeAccountCreationRequest {
  contact: string[];
  termsOfServiceAgreed: boolean;
  externalAccountBinding: {
    kid: string;
    signature: string;
  };
  key: any;
}

/**
 * ACME account creation response
 */
export interface AcmeAccountCreationResponse {
  status: string;
  contact: string[];
  orders: string;
}

/**
 * ACME order creation response
 */
export interface AcmeOrderCreationResponse {
  status: string;
  expires: string;
  identifiers: Array<{ type: string; value: string }>;
  authorizations: string[];
  finalize: string;
}

/**
 * ACME order finalization response
 */
export interface AcmeOrderFinalizationResponse {
  status: string;
  expires: string;
  identifiers: Array<{ type: string; value: string }>;
  authorizations: string[];
  finalize: string;
  certificate?: string;
}

/**
 * ACME certificate download response (can be plain or encrypted)
 */
export type AcmeCertificateDownloadResponse = string | {
  encryptedContent: string;
  encryptionMetadata: {
    algorithm: string;
    keyId: string;
    iv: string;
  };
};

/**
 * ACME settings
 */
export interface AcmeSettings {
  enabled: boolean;
  directory_url?: string;
  challenge_types: string[];
  certificate_validity_days: number;
  auto_provision_enabled: boolean;
  external_account_required: boolean;
}
