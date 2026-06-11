/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import type { AxiosInstance } from 'axios';
import type {
  // Consent Management
  UserConsentsResponse,
  ConsentUpdate,
  UpdateConsentResponse,

  // Data Export & Deletion
  DataExportRequest,
  DataExportResponse,
  DataDeletionRequest,
  DataDeletionResponse,

  // Data Breach Management
  BreachNotification,
  BreachReportResponse,
  BreachReportsListResponse,

  // DPO Management
  DPOInfo,
  UpdateDPOResponse,

  // Privacy Policy & Data Retention
  PrivacyPolicyResponse,
  DataRetentionPolicy,
} from '../types/gdprCompliance.types';

/**
 * GDPR Compliance API Service
 *
 * Handles all GDPR-related operations including:
 * - User data export (Right to Access - Article 15)
 * - User data deletion (Right to be Forgotten - Article 17)
 * - Consent management (Article 7)
 * - Data breach reporting (Articles 33 & 34)
 * - DPO information management
 * - Privacy policy and data retention policies
 *
 * @example
 * ```typescript
 * const gdprService = new GdprComplianceApiService(axiosInstance);
 *
 * // Export user data
 * const exportData = await gdprService.exportUserData('user123', {
 *   format: 'json',
 *   include_telemetry: true
 * });
 *
 * // Report data breach
 * const breach = await gdprService.reportDataBreach({
 *   breach_type: 'unauthorized_access',
 *   severity: 'high',
 *   affected_users: ['user1', 'user2']
 * });
 * ```
 */
export class GdprComplianceApiService {
  constructor(private api: AxiosInstance) {}

  // =========================================================================
  // User Data Export & Deletion (Articles 15 & 17)
  // =========================================================================

  /**
   * Export user data (Right to Access - GDPR Article 15)
   * Generates a downloadable archive of all user data
   *
   * @param userId - User ID to export data for
   * @param request - Export options (format, inclusions, encryption)
   * @returns Download URL, expiration time, and file size
   */
  async exportUserData(
    userId: string,
    request: DataExportRequest = {}
  ): Promise<DataExportResponse> {
    const response = await this.api.post(`/api/v1/gdpr/user/${userId}/export`, request);
    return response.data;
  }

  /**
   * Delete user data (Right to be Forgotten - GDPR Article 17)
   * Permanently deletes all user data with detailed deletion report
   *
   * @param userId - User ID to delete data for
   * @param request - Deletion confirmation and reason
   * @returns Deletion report with deleted record counts
   */
  async deleteUserData(
    userId: string,
    request: DataDeletionRequest
  ): Promise<DataDeletionResponse> {
    const response = await this.api.delete(`/api/v1/gdpr/user/${userId}/delete`, {
      data: request
    });
    return response.data;
  }

  // =========================================================================
  // Consent Management (Article 7)
  // =========================================================================

  /**
   * Get user consents
   * Retrieves all consent records for a user
   *
   * @param userId - User ID to get consents for
   * @returns List of user consents with status and expiration
   */
  async getUserConsents(userId: string): Promise<UserConsentsResponse> {
    const response = await this.api.get(`/api/v1/gdpr/consent/${userId}`);
    return response.data;
  }

  /**
   * Update user consent
   * Records or updates consent for a specific purpose
   *
   * @param userId - User ID to update consent for
   * @param consent - Consent update details
   * @returns Updated consent record
   */
  async updateUserConsent(
    userId: string,
    consent: ConsentUpdate
  ): Promise<UpdateConsentResponse> {
    const response = await this.api.put(`/api/v1/gdpr/consent/${userId}`, consent);
    return response.data;
  }

  // =========================================================================
  // Data Breach Management (Articles 33 & 34)
  // =========================================================================

  /**
   * Report data breach (GDPR Articles 33 & 34)
   * Reports a data breach to authorities (must be within 72 hours)
   *
   * @param notification - Breach details including severity and affected users
   * @returns Breach ID and 72-hour compliance status
   */
  async reportDataBreach(
    notification: BreachNotification
  ): Promise<BreachReportResponse> {
    const response = await this.api.post('/api/v1/gdpr/breach/report', notification);
    return response.data;
  }

  /**
   * Get data breach reports
   * Retrieves all reported data breaches with statistics
   *
   * @returns List of breach reports and summary statistics
   */
  async getBreachReports(): Promise<BreachReportsListResponse> {
    const response = await this.api.get('/api/v1/gdpr/breach/reports');
    return response.data;
  }

  // =========================================================================
  // DPO (Data Protection Officer) Management
  // =========================================================================

  /**
   * Get DPO information
   * Retrieves current Data Protection Officer contact details
   *
   * @returns DPO contact information and response time
   */
  async getDPOInfo(): Promise<DPOInfo> {
    const response = await this.api.get('/api/v1/gdpr/dpo');
    return response.data;
  }

  /**
   * Update DPO information
   * Updates Data Protection Officer contact details
   *
   * @param dpoInfo - Updated DPO information
   * @returns Confirmation and updated DPO info
   */
  async updateDPOInfo(dpoInfo: DPOInfo): Promise<UpdateDPOResponse> {
    const response = await this.api.put('/api/v1/gdpr/dpo', dpoInfo);
    return response.data;
  }

  // =========================================================================
  // Privacy Policy & Data Retention
  // =========================================================================

  /**
   * Get privacy policy
   * Retrieves current privacy policy version and URL
   *
   * @returns Privacy policy version, URL, and summary
   */
  async getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
    const response = await this.api.get('/api/v1/gdpr/privacy-policy');
    return response.data;
  }

  /**
   * Get data retention policy
   * Retrieves retention periods for different data types
   *
   * @returns Retention periods for each data category
   */
  async getDataRetentionPolicy(): Promise<DataRetentionPolicy> {
    const response = await this.api.get('/api/v1/gdpr/data-retention');
    return response.data;
  }
}
