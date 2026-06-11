/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Test file to validate shared contracts integration
 * This file can be removed after successful integration
 */

// Test import from shared contracts
import { 
  Device, 
  User, 
  Organization, 
  ApiResponse,
  ErrorCode 
} from '@shared/types/api-contracts';

// Test that types are accessible
export const testDevice: Partial<Device> = {
  id: 'test-device',
  device_id: 'TEST001',
  name: 'Test Device',
  organization_id: 'org-123',
  type: 'sensor',
  status: 'active'
};

export const testApiResponse: ApiResponse<Device> = {
  success: true,
  data: testDevice as Device,
  error: null,
  timestamp: new Date().toISOString()
};

// Export to prevent unused variable warnings
export { Device, User, Organization, ApiResponse, ErrorCode };