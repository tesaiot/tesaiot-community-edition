/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * System Monitoring API Service
 *
 * Handles all API operations for system health monitoring and metrics
 * Extracted from tesaApi.ts (lines 1259-1350) as part of Phase 2 refactoring
 *
 * @module SystemMonitoringApiService
 */

import { AxiosInstance } from 'axios';
import type {
  SystemHealth,
  RealtimeSystemHealthResponse,
  ContainerMetricsResponse,
  ResourceUsageTimelineResponse,
  MetricsTimeRange,
  DeviceMetricsPeriod
} from '../types/systemMonitoring.types';

/**
 * SystemMonitoringApiService
 *
 * Provides system monitoring and health check operations:
 * - System health status
 * - Real-time metrics
 * - Container monitoring
 * - Resource usage trends
 * - Device metrics
 *
 * @example
 * ```typescript
 * const service = new SystemMonitoringApiService(axiosInstance);
 * const health = await service.getSystemHealth();
 * const metrics = await service.getContainerMetrics();
 * ```
 */
export class SystemMonitoringApiService {
  constructor(private api: AxiosInstance) {}

  /**
   * Get basic system health status
   *
   * @returns System health with CPU, memory, disk, and service status
   * @throws {AxiosError} If request fails
   */
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await this.api.get('/api/admin/system/health');
    return response.data;
  }

  /**
   * Get real-time system health with detailed metrics
   *
   * Provides comprehensive view of all services and system resources
   *
   * @returns Real-time health status with service details and timeline
   * @throws {AxiosError} If request fails
   */
  async getRealtimeSystemHealth(): Promise<RealtimeSystemHealthResponse> {
    const response = await this.api.get('/api/v1/dashboard/realtime/system-health');
    return response.data;
  }

  /**
   * Get detailed real-time system health
   *
   * Extended version with additional diagnostic information
   *
   * @returns Detailed system health data
   * @throws {AxiosError} If request fails
   */
  async getRealtimeSystemHealthDetailed(): Promise<any> {
    const response = await this.api.get('/api/v1/dashboard/realtime/system-health/detail');
    return response.data;
  }

  /**
   * Get Docker container metrics
   *
   * Provides resource usage for all running containers
   *
   * @returns Container metrics with CPU, memory, network IO
   * @throws {AxiosError} If request fails
   */
  async getContainerMetrics(): Promise<ContainerMetricsResponse> {
    const response = await this.api.get('/api/v1/dashboard/monitoring');
    return response.data;
  }

  /**
   * Get resource usage timeline
   *
   * Historical data for CPU, memory, disk, and network usage
   *
   * @param timeRange - Time period for historical data (1h, 6h, 24h)
   * @returns Timeline with usage data and summary statistics
   * @throws {AxiosError} If request fails
   */
  async getResourceUsageTimeline(timeRange: MetricsTimeRange = '1h'): Promise<ResourceUsageTimelineResponse> {
    const response = await this.api.get('/api/v1/dashboard/usage/trends', {
      params: { time_range: timeRange }
    });
    return response.data;
  }

  /**
   * Get device-specific metrics
   *
   * Telemetry data for a specific device over time
   *
   * @param deviceId - Device identifier
   * @param period - Time period for metrics (1h, 24h, 7d, 30d)
   * @returns Device metrics data
   * @throws {AxiosError} If device not found or request fails
   */
  async getDeviceMetrics(deviceId: string, period: DeviceMetricsPeriod = '24h') {
    const response = await this.api.get(`/api/v1/devices/${deviceId}/metrics`, {
      params: { period },
    });
    return response.data;
  }
}
