/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Health Check API Types
 *
 * Example domain types following template patterns
 */

// ✅ BEST: Import common types from same directory
import type { ApiResponse } from './common.api.types';

/**
 * Health status enum
 */
export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy'
}

/**
 * Service health information
 */
export interface ServiceHealth {
  name: string;
  status: HealthStatus;
  uptime: number;
  responseTime?: number;
  lastCheck: string;
}

/**
 * System health entity
 */
export interface HealthEntity {
  overall: HealthStatus;
  services: ServiceHealth[];
  timestamp: string;
  version: string;
}

/**
 * Health check response
 */
export interface HealthResponse extends ApiResponse<HealthEntity> {
  data: HealthEntity;
}
