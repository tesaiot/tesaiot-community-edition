/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Incident Response Types
 * Type definitions for security incident management including:
 * - Incident creation and tracking
 * - Incident updates and resolution
 * - Incident statistics and reporting
 * - Response plan management
 */

// ============================================================================
// Security Incident
// ============================================================================

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';
export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'closed';

export interface SecurityIncident {
  id: string;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  type: string;
  description: string;
  affected_systems: string[];
  detection_time: string;
  response_time?: string;
  resolution_time?: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateIncidentRequest {
  title: string;
  severity: IncidentSeverity;
  type: string;
  description: string;
  affected_systems: string[];
}

export interface UpdateIncidentRequest {
  status?: string;
  severity?: string;
  assigned_to?: string;
  description?: string;
}

export interface IncidentFilters {
  status?: string;
  severity?: string;
  assigned_to?: string;
  date_from?: string;
  date_to?: string;
}

// ============================================================================
// Incident Updates
// ============================================================================

export interface IncidentUpdate {
  incident_id: string;
  message: string;
  status?: string;
  updated_by: string;
  timestamp: string;
}

export interface AddIncidentUpdateRequest {
  message: string;
  status?: string;
}

// ============================================================================
// Incident Resolution
// ============================================================================

export interface IncidentResolution {
  resolution_summary: string;
  root_cause?: string;
  preventive_measures?: string[];
}

export interface ResolveIncidentResponse {
  status: string;
  message: string;
  incident: SecurityIncident;
}

// ============================================================================
// Incident Statistics
// ============================================================================

export interface IncidentTrend {
  date: string;
  count: number;
}

export interface IncidentStatistics {
  total_incidents: number;
  open_incidents: number;
  mttr: number; // Mean Time To Resolve in hours
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  trend_last_30_days: IncidentTrend[];
}

// ============================================================================
// Incident Response Plan
// ============================================================================

export interface ResponsePhase {
  phase: string;
  description: string;
  actions: string[];
  responsible_parties: string[];
}

export interface ResponseContact {
  name: string;
  role: string;
  contact: string;
  availability: string;
}

export interface EscalationLevel {
  severity: string;
  notification_time: string;
  stakeholders: string[];
}

export interface IncidentResponsePlan {
  version: string;
  last_updated: string;
  phases: ResponsePhase[];
  contact_list: ResponseContact[];
  escalation_matrix: EscalationLevel[];
}
