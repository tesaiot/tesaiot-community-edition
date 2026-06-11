/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Health Check API Service
 *
 * Example service following template patterns
 */

// ✅ BEST: Use path aliases for base imports
import { apiClient } from '@/services/api/base/api-client';
import { handleApiError } from '@/services/api/utils/error-handler';

// ✅ GOOD: Relative imports for same-level types (1 level up)
import type {
  HealthEntity,
  HealthResponse
} from '../types/health.api.types';

/**
 * Health check service class
 *
 * Following class-based pattern from api-service.template.ts
 */
export class HealthApiService {
  private readonly basePath = '/api/health';

  /**
   * Get system health status
   */
  async getHealth(): Promise<HealthEntity> {
    try {
      const response = await apiClient.get<HealthResponse>(this.basePath);
      return response.data.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch system health');
    }
  }

  /**
   * Get specific service health
   */
  async getServiceHealth(serviceName: string): Promise<HealthEntity> {
    try {
      const response = await apiClient.get<HealthResponse>(
        `${this.basePath}/${serviceName}`
      );
      return response.data.data;
    } catch (error) {
      throw handleApiError(error, `Failed to fetch ${serviceName} health`);
    }
  }
}

// Export singleton instance
export const healthApi = new HealthApiService();
