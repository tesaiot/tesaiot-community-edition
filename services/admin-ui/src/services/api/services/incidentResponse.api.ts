/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import type { AxiosInstance } from 'axios';
import type {
  SecurityIncident,
  CreateIncidentRequest,
  UpdateIncidentRequest,
  IncidentFilters,
  IncidentUpdate,
  AddIncidentUpdateRequest,
  IncidentResolution,
  ResolveIncidentResponse,
  IncidentStatistics,
  IncidentResponsePlan,
} from '../types/incidentResponse.types';

/**
 * Incident Response API Service
 *
 * Handles all security incident management operations including:
 * - Incident creation and tracking
 * - Incident updates and timeline
 * - Incident resolution and closure
 * - Incident statistics and reporting
 * - Response plan management
 * - MTTR (Mean Time To Resolve) tracking
 *
 * @example
 * ```typescript
 * const incidentService = new IncidentResponseApiService(axiosInstance);
 *
 * // Create incident
 * const incident = await incidentService.createIncident({
 *   title: 'Unauthorized access detected',
 *   severity: 'high',
 *   type: 'security_breach',
 *   description: 'Multiple failed login attempts',
 *   affected_systems: ['auth-service', 'api-gateway']
 * });
 *
 * // Track progress
 * await incidentService.addIncidentUpdate(incident.id, {
 *   message: 'Investigating source IP address',
 *   status: 'investigating'
 * });
 *
 * // Resolve incident
 * await incidentService.resolveIncident(incident.id, {
 *   resolution_summary: 'Blocked malicious IP',
 *   root_cause: 'Brute force attack',
 *   preventive_measures: ['Enable rate limiting', 'Update firewall rules']
 * });
 * ```
 */
export class IncidentResponseApiService {
  constructor(private api: AxiosInstance) {}

  // =========================================================================
  // Incident Management
  // =========================================================================

  /**
   * Create new security incident
   * Initializes incident tracking with severity and affected systems
   *
   * @param incident - Incident details
   * @returns Created incident with ID and tracking info
   */
  async createIncident(
    incident: CreateIncidentRequest
  ): Promise<SecurityIncident> {
    const response = await this.api.post('/api/v1/incidents', incident);
    return response.data;
  }

  /**
   * Get all incidents with optional filters
   *
   * @param filters - Filter by status, severity, assignee, date range
   * @returns List of incidents matching filters
   */
  async getIncidents(
    filters?: IncidentFilters
  ): Promise<SecurityIncident[]> {
    const response = await this.api.get('/api/v1/incidents', {
      params: filters
    });
    return response.data;
  }

  /**
   * Get specific incident by ID
   *
   * @param incidentId - Incident ID
   * @returns Incident details with full timeline
   */
  async getIncident(incidentId: string): Promise<SecurityIncident> {
    const response = await this.api.get(`/api/v1/incidents/${incidentId}`);
    return response.data;
  }

  /**
   * Update incident details
   * Allows updating status, severity, assignee, and description
   *
   * @param incidentId - Incident ID to update
   * @param update - Fields to update
   * @returns Updated incident
   */
  async updateIncident(
    incidentId: string,
    update: UpdateIncidentRequest
  ): Promise<SecurityIncident> {
    const response = await this.api.put(
      `/api/v1/incidents/${incidentId}`,
      update
    );
    return response.data;
  }

  // =========================================================================
  // Incident Updates & Timeline
  // =========================================================================

  /**
   * Add update to incident timeline
   * Records investigation progress and status changes
   *
   * @param incidentId - Incident ID
   * @param update - Update message and optional status change
   * @returns Created update entry
   */
  async addIncidentUpdate(
    incidentId: string,
    update: AddIncidentUpdateRequest
  ): Promise<IncidentUpdate> {
    const response = await this.api.post(
      `/api/v1/incidents/${incidentId}/updates`,
      update
    );
    return response.data;
  }

  /**
   * Get all updates for an incident
   * Retrieves complete incident timeline
   *
   * @param incidentId - Incident ID
   * @returns List of incident updates ordered by timestamp
   */
  async getIncidentUpdates(incidentId: string): Promise<IncidentUpdate[]> {
    const response = await this.api.get(
      `/api/v1/incidents/${incidentId}/updates`
    );
    return response.data;
  }

  // =========================================================================
  // Incident Resolution
  // =========================================================================

  /**
   * Resolve incident
   * Records resolution, root cause analysis, and preventive measures
   *
   * @param incidentId - Incident ID to resolve
   * @param resolution - Resolution summary and analysis
   * @returns Resolved incident with closure info
   */
  async resolveIncident(
    incidentId: string,
    resolution: IncidentResolution
  ): Promise<ResolveIncidentResponse> {
    const response = await this.api.post(
      `/api/v1/incidents/${incidentId}/resolve`,
      resolution
    );
    return response.data;
  }

  // =========================================================================
  // Incident Statistics & Reporting
  // =========================================================================

  /**
   * Get incident statistics
   * Provides MTTR, incident distribution, and trends
   *
   * @returns Incident statistics with 30-day trend
   */
  async getIncidentStatistics(): Promise<IncidentStatistics> {
    const response = await this.api.get('/api/v1/incidents/statistics');
    return response.data;
  }

  /**
   * Get incident response plan
   * Retrieves current response plan with phases, contacts, and escalation matrix
   *
   * @returns Incident response plan details
   */
  async getIncidentResponsePlan(): Promise<IncidentResponsePlan> {
    const response = await this.api.get('/api/v1/incidents/response-plan');
    return response.data;
  }
}
