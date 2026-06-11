/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * System Monitoring Types
 *
 * Type definitions for system health monitoring and metrics
 * Extracted from tesaApi.ts as part of Phase 2 refactoring
 *
 * @module SystemMonitoringTypes
 */

/**
 * System health status
 */
export interface SystemHealth {
  cpu: number;
  memory: number;
  disk: number;
  services: {
    api: 'healthy' | 'degraded' | 'down';
    mqtt: 'healthy' | 'degraded' | 'down';
    database: 'healthy' | 'degraded' | 'down';
    vault: 'healthy' | 'degraded' | 'down';
  };
}

/**
 * Service health metrics
 */
export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime: string;
  lastCheck: string;
  metrics: {
    cpu: number;
    memory: number;
    requests?: number;
    errors?: number;
  };
}

/**
 * System metrics
 */
export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: number;
}

/**
 * Resource timeline entry
 */
export interface ResourceTimelineEntry {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
  network: number;
}

/**
 * Realtime system health response
 */
export interface RealtimeSystemHealthResponse {
  services: ServiceHealth[];
  system_metrics: SystemMetrics;
  resource_timeline: ResourceTimelineEntry[];
  last_updated: string;
}

/**
 * Container metrics
 */
export interface ContainerMetrics {
  name: string;
  status: string;
  cpu_percent: number;
  memory_usage: number;
  memory_limit: number;
  network_io: {
    rx_bytes: number;
    tx_bytes: number;
  };
  uptime: string;
}

/**
 * Container metrics response
 */
export interface ContainerMetricsResponse {
  containers: ContainerMetrics[];
  last_updated: string;
}

/**
 * Timeline entry for resource usage
 */
export interface ResourceUsageTimelineEntry {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: number;
}

/**
 * Resource usage summary
 */
export interface ResourceUsageSummary {
  avg_cpu: number;
  avg_memory: number;
  peak_cpu: number;
  peak_memory: number;
}

/**
 * Resource usage timeline response
 */
export interface ResourceUsageTimelineResponse {
  timeline: ResourceUsageTimelineEntry[];
  summary: ResourceUsageSummary;
  time_range: string;
}

/**
 * Time range for metrics queries
 */
export type MetricsTimeRange = '1h' | '6h' | '24h';

/**
 * Device metrics period
 */
export type DeviceMetricsPeriod = '1h' | '24h' | '7d' | '30d';
