/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
  params?: Array<{
    name: string;
    required: boolean;
    description: string;
  }>;
  body?: Record<string, any>;
}

/**
 * Certificate management API endpoints
 */
export const certificateApiEndpoints: ApiEndpoint[] = [
  {
    method: 'GET',
    path: '/api/v1/certificates',
    description: 'List all certificates',
    params: []
  },
  {
    method: 'POST',
    path: '/api/v1/certificates',
    description: 'Create a new certificate',
    params: [],
    body: {
      deviceId: 'device-123',
      organizationId: 'org-456',
      commonName: 'device-123.iot.example.com',
      keyAlgorithm: 'rsa',
      keySize: 2048
    }
  },
  {
    method: 'GET',
    path: '/api/v1/certificates/{certificateId}/',
    description: 'Get certificate details',
    params: [
      { name: 'certificateId', required: true, description: 'Certificate ID' }
    ]
  },
  {
    method: 'POST',
    path: '/api/v1/certificates/{deviceId}/renew/',
    description: 'Renew a certificate',
    params: [
      { name: 'deviceId', required: true, description: 'Device ID' }
    ]
  },
  {
    method: 'POST',
    path: '/api/v1/certificates/{deviceId}/revoke/',
    description: 'Revoke a certificate',
    params: [
      { name: 'deviceId', required: true, description: 'Device ID' }
    ],
    body: {
      reason: 'keyCompromise'
    }
  },
  {
    method: 'GET',
    path: '/api/v1/certificates/audit-trail',
    description: 'Get certificate audit trail',
    params: []
  },
  {
    method: 'POST',
    path: '/api/v1/certificates/bulk',
    description: 'Perform bulk operations on certificates',
    params: [],
    body: {
      action: 'renew',
      device_ids: ['device-1', 'device-2']
    }
  }
];

/**
 * Get base URL for API requests
 * @returns Base URL string
 */
export const getBaseUrl = (): string => {
  return '';
};

/**
 * Generate cURL command examples
 * @param baseUrl - Base URL for the API
 * @returns Object with cURL command examples
 */
export const getCurlExamples = (baseUrl: string) => ({
  create: `curl -X POST ${baseUrl}/api/v1/certificates/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "deviceId": "device-123",
    "organizationId": "org-456",
    "commonName": "device-123.iot.example.com",
    "keyAlgorithm": "rsa",
    "keySize": 2048
  }'`,
  
  renew: `curl -X POST ${baseUrl}/api/v1/certificates/{deviceId}/renew/ \\
  -H "Authorization: Bearer YOUR_TOKEN"`,
  
  revoke: `curl -X POST ${baseUrl}/api/v1/certificates/{deviceId}/revoke/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "reason": "keyCompromise"
  }'`
});