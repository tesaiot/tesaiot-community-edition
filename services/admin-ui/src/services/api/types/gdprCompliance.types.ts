/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * GDPR Compliance Types
 * Type definitions for GDPR compliance operations including:
 * - User data export and deletion
 * - Consent management
 * - Data breach reporting
 * - DPO (Data Protection Officer) information
 * - Privacy policy and data retention
 */

// ============================================================================
// User Consent Management
// ============================================================================

export interface UserConsent {
  purpose: string;
  consent_given: boolean;
  timestamp: string;
  expires_at?: string;
  active: boolean;
  consent_version: string;
}

export interface ConsentUpdate {
  purpose: string;
  consent_given: boolean;
  expires_at?: string;
}

export interface UserConsentsResponse {
  status: string;
  user_id: string;
  consents: UserConsent[];
}

export interface UpdateConsentResponse {
  status: string;
  message: string;
  consent: UserConsent;
}

// ============================================================================
// Data Export & Deletion (Right to Access & Right to be Forgotten)
// ============================================================================

export interface DataExportRequest {
  format?: 'json' | 'csv' | 'xml';
  include_telemetry?: boolean;
  include_logs?: boolean;
  password_protect?: boolean;
}

export interface DataExportResponse {
  status: string;
  message: string;
  download_url: string;
  expires_in: string;
  size_bytes: number;
}

export interface DataDeletionRequest {
  confirm_user_id: string;
  deletion_reason: string;
  immediate?: boolean;
}

export interface DataDeletionReport {
  user_id: string;
  deletion_timestamp: string;
  reason: string;
  deleted_records: Record<string, number>;
}

export interface DataDeletionResponse {
  status: string;
  message: string;
  deletion_report: DataDeletionReport;
}

// ============================================================================
// Data Breach Management (Article 33 & 34 Notifications)
// ============================================================================

export interface BreachNotification {
  breach_type: string;
  affected_data: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  affected_users: string[];
  discovered_at: string;
  description: string;
}

export interface BreachReport {
  breach_id: string;
  breach_type: string;
  affected_data: string[];
  severity: string;
  affected_users: string[];
  discovered_at: string;
  reported_at: string;
  description: string;
  status: string;
  within_72_hours: boolean;
  dpa_notified: boolean;
  users_notified: boolean;
}

export interface BreachReportResponse {
  status: string;
  message: string;
  breach_id: string;
  within_72_hours: boolean;
}

export interface BreachReportsListResponse {
  status: string;
  breaches: BreachReport[];
  statistics: {
    total_breaches: number;
    within_72_hours: number;
    by_severity: Record<string, number>;
  };
}

// ============================================================================
// DPO (Data Protection Officer) Management
// ============================================================================

export interface DPOInfo {
  title: string;
  email: string;
  phone: string;
  address: string;
  response_time: string;
}

export interface UpdateDPOResponse {
  status: string;
  message: string;
  dpo_info: DPOInfo;
}

// ============================================================================
// Privacy Policy & Data Retention
// ============================================================================

export interface PrivacyPolicyResponse {
  version: string;
  last_updated: string;
  policy_url: string;
  summary: string;
}

export interface DataRetentionPolicy {
  telemetry_data: string;
  user_profiles: string;
  activity_logs: string;
  security_logs: string;
  deleted_data: string;
}
